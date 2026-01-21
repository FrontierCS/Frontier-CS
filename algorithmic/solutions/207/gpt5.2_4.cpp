#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr int BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char readChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = readChar();
        }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
    }
};

struct FastOutput {
    static constexpr int BUFSIZE = 1 << 20;
    int idx = 0;
    char buf[BUFSIZE];

    ~FastOutput() { flush(); }

    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }

    inline void writeChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }

    template <class T>
    inline void writeInt(T x, char endc) {
        if (x == 0) {
            writeChar('0');
            writeChar(endc);
            return;
        }
        if constexpr (std::is_signed<T>::value) {
            if (x < 0) {
                writeChar('-');
                x = -x;
            }
        }
        char s[32];
        int n = 0;
        while (x > 0) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        while (n--) writeChar(s[n]);
        writeChar(endc);
    }

    inline void writeString(const string &s, char endc) {
        for (char c : s) writeChar(c);
        writeChar(endc);
    }
};

static string toStringInt128(__int128 x) {
    if (x == 0) return "0";
    bool neg = false;
    if (x < 0) { neg = true; x = -x; }
    string s;
    while (x > 0) {
        int d = int(x % 10);
        s.push_back(char('0' + d));
        x /= 10;
    }
    if (neg) s.push_back('-');
    reverse(s.begin(), s.end());
    return s;
}

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

    // Compute G_M as mapping g_final: transformed index -> physical index after all Jerry swaps.
    vector<int> g_final(N), p_final(N);
    iota(g_final.begin(), g_final.end(), 0);
    iota(p_final.begin(), p_final.end(), 0);

    for (int k = 0; k < M; k++) {
        int x = X[k], y = Y[k];
        int ix = p_final[x], iy = p_final[y];
        swap(g_final[ix], g_final[iy]);
        swap(p_final[x], p_final[y]);
    }

    // Build inverse of target permutation T = g_final (values are physical indices).
    vector<int> invT(N);
    for (int i = 0; i < N; i++) invT[g_final[i]] = i;

    // Q[i] = where element at i should go (target position of current value S[i]).
    vector<int> Q(N);
    for (int i = 0; i < N; i++) Q[i] = invT[S[i]];

    // Minimal swaps to transform S into g_final in transformed coordinates via cycle decomposition.
    vector<char> vis(N, 0);
    vector<pair<int,int>> transSwaps;
    transSwaps.reserve(N);

    for (int i = 0; i < N; i++) {
        if (vis[i]) continue;
        int cur = i;
        vector<int> cyc;
        while (!vis[cur]) {
            vis[cur] = 1;
            cyc.push_back(cur);
            cur = Q[cur];
        }
        if ((int)cyc.size() > 1) {
            for (int t = 1; t < (int)cyc.size(); t++) {
                transSwaps.emplace_back(cyc[0], cyc[t]);
            }
        }
    }

    int K = (int)transSwaps.size();
    if (K > M) {
        // Should not happen given the problem guarantee.
        // Fallback: no-op (still output something valid if possible).
        K = M;
    }

    // Output R = M rounds.
    fo.writeInt(M, '\n');

    // Forward simulate Jerry to map transformed swaps to physical indices each round.
    vector<int> g_cur(N), p_cur(N);
    iota(g_cur.begin(), g_cur.end(), 0);
    iota(p_cur.begin(), p_cur.end(), 0);

    long long sumCost = 0;

    for (int k = 0; k < M; k++) {
        int x = X[k], y = Y[k];
        int ix = p_cur[x], iy = p_cur[y];
        swap(g_cur[ix], g_cur[iy]);
        swap(p_cur[x], p_cur[y]);

        int a = 0, b = 0;
        if (k < K) {
            a = transSwaps[k].first;
            b = transSwaps[k].second;
        }

        int u = g_cur[a];
        int v = g_cur[b];
        sumCost += llabs((long long)u - (long long)v);

        fo.writeInt(u, ' ');
        fo.writeInt(v, '\n');
    }

    __int128 V = (__int128)M * (__int128)sumCost;
    fo.writeString(toStringInt128(V), '\n');
    return 0;
}