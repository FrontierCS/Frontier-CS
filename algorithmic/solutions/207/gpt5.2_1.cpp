#include <bits/stdc++.h>
using namespace std;

class FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t pos = 0, len = 0;

    inline char getChar() {
        if (pos >= len) {
            len = fread(buf, 1, BUFSIZE, stdin);
            pos = 0;
            if (len == 0) return 0;
        }
        return buf[pos++];
    }

public:
    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = getChar();
            if (!c) return false;
        } while (c <= ' ');
        bool neg = false;
        if (c == '-') {
            neg = true;
            c = getChar();
        }
        long long val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = getChar();
        }
        out = neg ? (T)-val : (T)val;
        return true;
    }
};

class FastOutput {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0;

    inline void flushBuf() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }

public:
    ~FastOutput() { flushBuf(); }

    inline void writeChar(char c) {
        if (idx >= BUFSIZE) flushBuf();
        buf[idx++] = c;
    }

    template <class T>
    inline void writeInt(T x) {
        if (x == 0) {
            writeChar('0');
            return;
        }
        if (x < 0) {
            writeChar('-');
            x = -x;
        }
        char s[32];
        int n = 0;
        while (x > 0) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        while (n--) writeChar(s[n]);
    }

    inline void writeSpace() { writeChar(' '); }
    inline void writeNewline() { writeChar('\n'); }
};

int main() {
    FastScanner fs;
    FastOutput fo;

    int N;
    if (!fs.readInt(N)) return 0;

    vector<int> S(N);
    for (int i = 0; i < N; i++) fs.readInt(S[i]);

    int M;
    fs.readInt(M);

    vector<int> X(M), Y(M);
    for (int i = 0; i < M; i++) {
        fs.readInt(X[i]);
        fs.readInt(Y[i]);
    }

    if (M == 0) {
        // Best-effort fallback; instances should still be solvable per statement.
        fo.writeInt(0);
        fo.writeNewline();
        fo.writeInt(0);
        fo.writeNewline();
        return 0;
    }

    // Target permutation T: T(i) = position where value i is in initial array.
    vector<int> pos0(N);
    for (int i = 0; i < N; i++) pos0[S[i]] = i;

    // Compute J = j0 j1 ... j_{M-1} (composition on the right), as mapping array Jmap[i] = J(i).
    vector<int> Jmap(N);
    iota(Jmap.begin(), Jmap.end(), 0);
    for (int k = 0; k < M; k++) {
        int a = X[k], b = Y[k];
        if (a != b) swap(Jmap[a], Jmap[b]);
    }

    // invJ[v] = J^{-1}(v)
    vector<int> invJ(N);
    for (int i = 0; i < N; i++) invJ[Jmap[i]] = i;

    // U = J^{-1} * T  => U(i) = invJ[ pos0[i] ]
    vector<int> U(N);
    for (int i = 0; i < N; i++) U[i] = invJ[pos0[i]];

    // Decompose U into transpositions (minimal): for each cycle, (c0 c_{l-1})...(c0 c1)
    vector<char> vis(N, 0);
    vector<pair<int,int>> q_list;
    q_list.reserve(N);

    for (int i = 0; i < N; i++) {
        if (vis[i]) continue;
        int cur = i;
        vector<int> cyc;
        while (!vis[cur]) {
            vis[cur] = 1;
            cyc.push_back(cur);
            cur = U[cur];
        }
        if ((int)cyc.size() <= 1) continue;
        int c0 = cyc[0];
        for (int t = (int)cyc.size() - 1; t >= 1; t--) {
            q_list.emplace_back(c0, cyc[t]);
        }
    }

    int L = (int)q_list.size();
    // Problem guarantees solvable within M rounds, thus L <= M.
    if (L > M) {
        // Should not happen; output something harmless.
        L = M;
        q_list.resize(M);
    }

    // Build q_k array length M, place needed transpositions at the end.
    vector<pair<int,int>> q(M, {0, 0});
    for (int t = 0; t < L; t++) q[M - L + t] = q_list[t];

    // Compute p_k = S_k q_k S_k^{-1}, where S_k = j_{k+1}...j_{M-1}.
    // Maintain S_k forward mapping f and inverse inv. Start with S_{M-1} = Id.
    vector<int> f(N), inv(N);
    iota(f.begin(), f.end(), 0);
    iota(inv.begin(), inv.end(), 0);

    vector<pair<int,int>> p(M);

    for (int k = M - 1; k >= 0; k--) {
        int a = q[k].first, b = q[k].second;
        int u = f[a];
        int v = f[b];
        p[k] = {u, v};

        // Update S_{k-1} = j_k ∘ S_k : swap outputs X[k], Y[k]
        int x = X[k], y = Y[k];
        if (x != y) {
            int ix = inv[x], iy = inv[y];
            swap(f[ix], f[iy]);
            swap(inv[x], inv[y]);
        }
    }

    long long sumCost = 0;
    for (int k = 0; k < M; k++) {
        sumCost += llabs((long long)p[k].first - (long long)p[k].second);
    }
    long long V = sumCost * (long long)M;

    fo.writeInt(M);
    fo.writeNewline();
    for (int k = 0; k < M; k++) {
        fo.writeInt(p[k].first);
        fo.writeSpace();
        fo.writeInt(p[k].second);
        fo.writeNewline();
    }
    fo.writeInt(V);
    fo.writeNewline();

    return 0;
}