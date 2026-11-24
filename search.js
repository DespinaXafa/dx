// Αναζήτηση ΜΟΝΟ σε τίτλο + περιγραφή του ΜΙΤΟΣ.
// lexical: ίδια υλοποίηση με sklearn TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5), sublinear_tf=True)
// semantic: multilingual-e5-small (doc embeddings προϋπολογισμένα, int8) + cosine
// hybrid: Reciprocal Rank Fusion, k = 60
export const RRF_K = 60;

export function norm(s) {
  return s.toLowerCase().normalize("NFD").replace(/\p{Mn}/gu, "").replace(/ς/g, "σ");
}

function charWb(text, minN = 3, maxN = 5) {
  const out = [];
  for (const w0 of text.split(/\s+/)) {
    if (!w0) continue;
    const w = [..." " + w0 + " "];                 // code points, όπως η Python
    for (let n = minN; n <= maxN; n++) {
      let off = 0;
      out.push(w.slice(off, off + n).join(""));
      while (off + n < w.length) { off++; out.push(w.slice(off, off + n).join("")); }
      if (off === 0) break;
    }
  }
  return out;
}

function tfVec(grams) {
  const tf = new Map();
  for (const g of grams) tf.set(g, (tf.get(g) || 0) + 1);
  return tf;
}

export class Lexical {
  constructor(texts) {
    const N = texts.length, df = new Map(), docs = [];
    for (const t of texts) {
      const tf = tfVec(charWb(norm(t)));
      docs.push(tf);
      for (const g of tf.keys()) df.set(g, (df.get(g) || 0) + 1);
    }
    this.idf = new Map();
    for (const [g, d] of df) this.idf.set(g, Math.log((1 + N) / (1 + d)) + 1);
    this.post = new Map();                          // ngram -> [docIdx, weight, ...]
    docs.forEach((tf, i) => {
      let ss = 0; const w = [];
      for (const [g, c] of tf) { const v = (1 + Math.log(c)) * this.idf.get(g); w.push([g, v]); ss += v * v; }
      const nrm = Math.sqrt(ss) || 1;
      for (const [g, v] of w) { let a = this.post.get(g); if (!a) this.post.set(g, a = []); a.push(i, v / nrm); }
    });
    this.N = N;
  }
  scores(q) {
    const s = new Float64Array(this.N);
    const tf = tfVec(charWb(norm(q)));
    let ss = 0; const w = [];
    for (const [g, c] of tf) { const idf = this.idf.get(g); if (!idf) continue; const v = (1 + Math.log(c)) * idf; w.push([g, v]); ss += v * v; }
    const nrm = Math.sqrt(ss) || 1;
    for (const [g, v] of w) { const a = this.post.get(g); for (let k = 0; k < a.length; k += 2) s[a[k]] += a[k + 1] * v / nrm; }
    return s;
  }
}

export function semanticScores(emb, dim, qv) {      // emb: Int8Array N*dim, qv: Float32Array (L2-normalized)
  const N = emb.length / dim, s = new Float64Array(N);
  for (let i = 0; i < N; i++) { let d = 0; const o = i * dim; for (let j = 0; j < dim; j++) d += emb[o + j] * qv[j]; s[i] = d / 127; }
  return s;
}

export function order(scores) {                      // σταθερή ταξινόμηση, όπως np.argsort(kind="stable")
  return Array.from(scores.keys()).sort((a, b) => (scores[b] - scores[a]) || (a - b));
}

export function rrf(...scoreArrays) {
  const N = scoreArrays[0].length, out = new Float64Array(N);
  for (const s of scoreArrays) order(s).forEach((doc, r) => { out[doc] += 1 / (RRF_K + r + 1); });
  return out;
}
