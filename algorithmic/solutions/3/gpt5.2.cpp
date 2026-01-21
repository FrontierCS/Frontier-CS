#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static inline int gc() { return getchar_unlocked(); }
    int nextInt() {
        int c = gc();
        while (c <= 32 && c != EOF) c = gc();
        if (c == EOF) return INT_MIN;
        int sgn = 1;
        if (c == '-') { sgn = -1; c = gc(); }
        int x = 0;
        while (c > 32 && c != EOF) {
            x = x * 10 + (c - '0');
            c = gc();
        }
        return x * sgn;
    }
} In;

static inline long long mod_pow(long long a, long long e, long long mod) {
    long long r = 1 % mod;
    a %= mod;
    while (e > 0) {
        if (e & 1) r = (__int128)r * a % mod;
        a = (__int128)a * a % mod;
        e >>= 1;
    }
    return r;
}

static inline long long mod_inv(long long a, long long mod) {
    return mod_pow(a, mod - 2, mod);
}

static long long tonelli_shanks(long long n, long long p) {
    if (n == 0) return 0;
    if (p == 2) return n;
    if (mod_pow(n, (p - 1) / 2, p) != 1) return -1; // no sqrt
    if (p % 4 == 3) return mod_pow(n, (p + 1) / 4, p);

    long long q = p - 1;
    int s = 0;
    while ((q & 1) == 0) { q >>= 1; s++; }

    long long z = 2;
    while (mod_pow(z, (p - 1) / 2, p) != p - 1) z++;

    long long c = mod_pow(z, q, p);
    long long x = mod_pow(n, (q + 1) / 2, p);
    long long t = mod_pow(n, q, p);
    int m = s;

    while (t != 1) {
        int i = 1;
        long long tt = (__int128)t * t % p;
        while (i < m && tt != 1) {
            tt = (__int128)tt * tt % p;
            i++;
        }
        long long b = mod_pow(c, 1LL << (m - i - 1), p);
        x = (__int128)x * b % p;
        long long b2 = (__int128)b * b % p;
        t = (__int128)t * b2 % p;
        c = b2;
        m = i;
    }
    return x;
}

static inline void appendInt(string &s, int x) {
    char buf[24];
    int n = 0;
    if (x == 0) {
        s.push_back('0');
        return;
    }
    if (x < 0) {
        s.push_back('-');
        x = -x;
    }
    while (x > 0) {
        buf[n++] = char('0' + (x % 10));
        x /= 10;
    }
    while (n--) s.push_back(buf[n]);
}

static inline void writeQuerySmall(const vector<int> &ops) {
    printf("%d", (int)ops.size());
    for (int x : ops) printf(" %d", x);
    printf("\n");
    fflush(stdout);
}

static inline vector<int> readAnswersSmall(int L) {
    vector<int> ans(L);
    for (int i = 0; i < L; i++) {
        int v = In.nextInt();
        if (v == INT_MIN) exit(0);
        ans[i] = v;
    }
    return ans;
}

struct InteractiveSolver {
    int n;
    vector<char> inI;
    vector<int> I, B;
    vector<char> litI; // by index in I

    // Query for a subset defined on I by desired bit (type=0: x, type=1: y), bit pos, wantBit (0/1)
    // Returns for each b in B whether b has at least one neighbor in current lit subset.
    vector<char> scanB(int type, int bit, int wantBit, const vector<int> &yvals, int bits) {
        vector<int> diffOps;
        diffOps.reserve(I.size() / 2 + 16);

        for (int idx = 0; idx < (int)I.size(); idx++) {
            int xval = idx + 1;
            int val = (type == 0 ? xval : yvals[idx]);
            int b = (val >> bit) & 1;
            char desired = (b == wantBit) ? 1 : 0;
            if (litI[idx] != desired) {
                litI[idx] = desired;
                diffOps.push_back(I[idx]);
            }
        }

        int diffLen = (int)diffOps.size();
        int Bsz = (int)B.size();
        int L = diffLen + 2 * Bsz;

        string out;
        out.reserve((size_t)12 * (size_t)(L + 2));
        appendInt(out, L);
        for (int v : diffOps) {
            out.push_back(' ');
            appendInt(out, v);
        }
        for (int v : B) {
            out.push_back(' ');
            appendInt(out, v);
            out.push_back(' ');
            appendInt(out, v);
        }
        out.push_back('\n');

        fwrite(out.data(), 1, out.size(), stdout);
        fflush(stdout);

        // Read answers
        for (int i = 0; i < diffLen; i++) {
            int t = In.nextInt();
            if (t == INT_MIN) exit(0);
        }
        vector<char> res(Bsz);
        for (int j = 0; j < Bsz; j++) {
            int on = In.nextInt();
            if (on == INT_MIN) exit(0);
            res[j] = (char)on;
            int off = In.nextInt();
            if (off == INT_MIN) exit(0);
            (void)off;
        }
        return res;
    }

    void solve() {
        int subtask = In.nextInt();
        (void)subtask;
        n = In.nextInt();
        if (n == INT_MIN) return;

        inI.assign(n + 1, 0);
        I.clear(); I.reserve(n);
        int pending = 0;

        // Greedy maximal independent set, keeping accepted vertices lit. Rejected vertices left lit as pending, removed at start of next query.
        for (int v = 1; v <= n; v++) {
            if (pending == 0) {
                writeQuerySmall({v});
                auto ans = readAnswersSmall(1);
                if (ans[0] == 0) {
                    inI[v] = 1;
                    I.push_back(v);
                } else {
                    pending = v; // left ON, will remove next step
                }
            } else {
                writeQuerySmall({pending, v});
                auto ans = readAnswersSmall(2);
                pending = 0; // first op removed it
                if (ans[1] == 0) {
                    inI[v] = 1;
                    I.push_back(v);
                } else {
                    pending = v; // left ON
                }
            }
        }
        if (pending != 0) {
            writeQuerySmall({pending});
            auto ans = readAnswersSmall(1);
            (void)ans;
            pending = 0;
        }

        B.clear(); B.reserve(n - (int)I.size());
        for (int v = 1; v <= n; v++) if (!inI[v]) B.push_back(v);

        int m = (int)I.size();
        int Bsz = (int)B.size();

        // Prepare lit state for I: currently all accepted vertices are lit (I is lit).
        litI.assign(m, 1);

        static const long long MOD = 65537; // prime > 1e5/2
        static const int BITS = 17;         // since MOD < 2^17

        vector<int> yvals(m);
        for (int i = 0; i < m; i++) {
            long long x = i + 1;
            yvals[i] = (int)((__int128)x * x % MOD);
        }

        vector<uint32_t> sumX(Bsz, 0), sumY(Bsz, 0);
        vector<uint8_t> carryX(Bsz, 0), carryY(Bsz, 0);

        // Process bits for x
        for (int bit = 0; bit < BITS; bit++) {
            auto ones = scanB(0, bit, 1, yvals, BITS);
            auto zeros = scanB(0, bit, 0, yvals, BITS);
            for (int j = 0; j < Bsz; j++) {
                int OR = ones[j];
                int z = zeros[j];
                int c;
                if (OR == 0) c = 0;
                else if (z == 0) c = 2;
                else c = 1;
                int total = c + carryX[j];
                if (total & 1) sumX[j] |= (1u << bit);
                carryX[j] = (uint8_t)(total >> 1);
            }
        }
        for (int j = 0; j < Bsz; j++) {
            if (carryX[j]) sumX[j] |= (uint32_t)carryX[j] << BITS;
        }

        // Process bits for y = x^2 mod MOD
        for (int bit = 0; bit < BITS; bit++) {
            auto ones = scanB(1, bit, 1, yvals, BITS);
            auto zeros = scanB(1, bit, 0, yvals, BITS);
            for (int j = 0; j < Bsz; j++) {
                int OR = ones[j];
                int z = zeros[j];
                int c;
                if (OR == 0) c = 0;
                else if (z == 0) c = 2;
                else c = 1;
                int total = c + carryY[j];
                if (total & 1) sumY[j] |= (1u << bit);
                carryY[j] = (uint8_t)(total >> 1);
            }
        }
        for (int j = 0; j < Bsz; j++) {
            if (carryY[j]) sumY[j] |= (uint32_t)carryY[j] << BITS;
        }

        // Build adjacency
        vector<array<int,2>> adj(n + 1);
        vector<char> deg(n + 1, 0);

        auto addEdge = [&](int u, int v) {
            if (deg[u] >= 2 || deg[v] >= 2) return; // avoid overflow if something goes wrong
            adj[u][deg[u]++] = v;
            adj[v][deg[v]++] = u;
        };

        long long inv2 = (MOD + 1) / 2;

        vector<int> specialB;

        for (int j = 0; j < Bsz; j++) {
            long long sx = (long long)sumX[j];
            long long sy = (long long)sumY[j];

            long long s = sx % MOD;
            long long sqsum = sy % MOD;

            long long ss = (__int128)s * s % MOD;
            long long p = (ss - sqsum) % MOD;
            if (p < 0) p += MOD;
            p = (__int128)p * inv2 % MOD;

            long long disc = (ss - (__int128)4 * p) % MOD;
            if (disc < 0) disc += MOD;

            if (disc == 0) {
                long long x = (__int128)s * inv2 % MOD;
                int xi = (int)x;
                if (xi <= 0 || xi > m) xi = 1; // fallback
                int neighI = I[xi - 1];
                int b = B[j];
                addEdge(b, neighI);
                specialB.push_back(b);
            } else {
                long long r = tonelli_shanks(disc, MOD);
                if (r < 0) r = 0;
                long long x1 = (__int128)(s + r) * inv2 % MOD;
                long long x2 = (__int128)(s - r + MOD) * inv2 % MOD;
                int a = (int)x1, b = (int)x2;

                // Ensure in range by swapping with MOD-x? (should not be needed)
                if (a <= 0 || a > m) {
                    int aa = (int)((MOD - x1) % MOD);
                    if (aa >= 1 && aa <= m) a = aa;
                }
                if (b <= 0 || b > m) {
                    int bb = (int)((MOD - x2) % MOD);
                    if (bb >= 1 && bb <= m) b = bb;
                }

                int v1 = I[a - 1];
                int v2 = I[b - 1];
                int bj = B[j];
                addEdge(bj, v1);
                addEdge(bj, v2);
            }
        }

        if (n % 2 == 1) {
            if ((int)specialB.size() != 2) {
                // fallback: try to find missing special by degree
                for (int v : B) if (deg[v] == 1) specialB.push_back(v);
            }
            if ((int)specialB.size() >= 2) addEdge(specialB[0], specialB[1]);
        }

        // Ensure all degrees 2 (best effort)
        // Traverse cycle
        vector<int> order;
        order.reserve(n);
        int start = 1;
        int prev = 0, cur = start;
        for (int i = 0; i < n; i++) {
            order.push_back(cur);
            int nxt;
            if (deg[cur] == 0) {
                nxt = start; // broken
            } else if (deg[cur] == 1) {
                nxt = adj[cur][0];
            } else {
                nxt = (prev == 0 ? adj[cur][0] : (adj[cur][0] == prev ? adj[cur][1] : adj[cur][0]));
            }
            prev = cur;
            cur = nxt;
        }

        printf("-1");
        for (int x : order) printf(" %d", x);
        printf("\n");
        fflush(stdout);
        exit(0);
    }
};

int main() {
    setvbuf(stdout, nullptr, _IOFBF, 1 << 20);
    InteractiveSolver solver;
    solver.solve();
    return 0;
}