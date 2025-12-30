#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, sz;
    DSU() {}
    DSU(int n): n(n), p(n), sz(n,1) {
        iota(p.begin(), p.end(), 0);
    }
    int find(int x){ return p[x]==x?x:p[x]=find(p[x]); }
    bool unite(int a, int b){
        a=find(a); b=find(b);
        if(a==b) return false;
        if(sz[a]<sz[b]) swap(a,b);
        p[b]=a; sz[a]+=sz[b];
        return true;
    }
};

static inline int hexCharToInt(char c) {
    if ('0' <= c && c <= '9') return c - '0';
    if ('a' <= c && c <= 'f') return 10 + (c - 'a');
    if ('A' <= c && c <= 'F') return 10 + (c - 'A');
    return 0;
}

struct XorShift64 {
    uint64_t x;
    XorShift64() {
        uint64_t t = chrono::high_resolution_clock::now().time_since_epoch().count();
        x = t ^ (t<<7) ^ (t>>9) ^ 0x9e3779b97f4a7c15ULL;
        if (!x) x = 88172645463393265ULL;
    }
    inline uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline uint32_t nextUInt(uint32_t mod) {
        return (uint32_t)(next() % mod);
    }
};

struct Solver {
    int N;
    int Tlim;
    int n2;
    vector<unsigned char> board;
    int zi, zj; // empty position
    string answer;
    XorShift64 rng;

    int calcE(const vector<unsigned char> &b) {
        int E = 0;
        for (int i = 0; i < N-1; ++i) for (int j = 0; j < N; ++j) {
            int id1 = i*N + j, id2 = (i+1)*N + j;
            unsigned char a = b[id1], d = b[id2];
            if (!a || !d) continue;
            if ((a & 8) && (d & 2)) ++E;
        }
        for (int i = 0; i < N; ++i) for (int j = 0; j < N-1; ++j) {
            int id1 = i*N + j, id2 = i*N + (j+1);
            unsigned char a = b[id1], r = b[id2];
            if (!a || !r) continue;
            if ((a & 4) && (r & 1)) ++E;
        }
        return E;
    }

    int calcS(const vector<unsigned char> &b) {
        DSU uf(n2);
        // Unite edges
        for (int i = 0; i < N-1; ++i) for (int j = 0; j < N; ++j) {
            int id1 = i*N + j, id2 = (i+1)*N + j;
            unsigned char a = b[id1], d = b[id2];
            if (!a || !d) continue;
            if ((a & 8) && (d & 2)) uf.unite(id1, id2);
        }
        for (int i = 0; i < N; ++i) for (int j = 0; j < N-1; ++j) {
            int id1 = i*N + j, id2 = i*N + (j+1);
            unsigned char a = b[id1], r = b[id2];
            if (!a || !r) continue;
            if ((a & 4) && (r & 1)) uf.unite(id1, id2);
        }
        vector<int> vert(n2,0), edges(n2,0);
        for (int id = 0; id < n2; ++id) {
            if (!b[id]) continue;
            int r = uf.find(id);
            vert[r]++;
        }
        for (int i = 0; i < N-1; ++i) for (int j = 0; j < N; ++j) {
            int id1 = i*N + j, id2 = (i+1)*N + j;
            unsigned char a = b[id1], d = b[id2];
            if (!a || !d) continue;
            if ((a & 8) && (d & 2)) {
                int r = uf.find(id1);
                edges[r]++;
            }
        }
        for (int i = 0; i < N; ++i) for (int j = 0; j < N-1; ++j) {
            int id1 = i*N + j, id2 = i*N + (j+1);
            unsigned char a = b[id1], r2 = b[id2];
            if (!a || !r2) continue;
            if ((a & 4) && (r2 & 1)) {
                int r = uf.find(id1);
                edges[r]++;
            }
        }
        int best = 0;
        for (int i = 0; i < n2; ++i) {
            if (vert[i] > 0 && edges[i] == vert[i] - 1) {
                if (vert[i] > best) best = vert[i];
            }
        }
        return best;
    }

    inline bool canMove(char d, int r, int c) const {
        if (d=='U') return r>0;
        if (d=='D') return r+1<N;
        if (d=='L') return c>0;
        if (d=='R') return c+1<N;
        return false;
    }

    inline void applyMove(vector<unsigned char>& b, int &r, int &c, char d) {
        if (d=='U') {
            int nr=r-1,nc=c;
            swap(b[r*N+c], b[nr*N+nc]); r=nr; c=nc;
        } else if (d=='D') {
            int nr=r+1,nc=c;
            swap(b[r*N+c], b[nr*N+nc]); r=nr; c=nc;
        } else if (d=='L') {
            int nr=r,nc=c-1;
            swap(b[r*N+c], b[nr*N+nc]); r=nr; c=nc;
        } else if (d=='R') {
            int nr=r,nc=c+1;
            swap(b[r*N+c], b[nr*N+nc]); r=nr; c=nc;
        }
    }

    inline char opposite(char d) {
        if (d=='U') return 'D';
        if (d=='D') return 'U';
        if (d=='L') return 'R';
        if (d=='R') return 'L';
        return '?';
    }

    string randomPath(int L, int sr, int sc) {
        string path;
        path.reserve(L);
        int r = sr, c = sc;
        char last = '?';
        for (int k = 0; k < L; ++k) {
            char cand[4] = {'U','D','L','R'};
            char opts[4];
            int cnt = 0;
            for (int t = 0; t < 4; ++t) {
                char d = cand[t];
                if (!canMove(d, r, c)) continue;
                if (last != '?' && d == opposite(last)) continue;
                opts[cnt++] = d;
            }
            if (cnt == 0) {
                // only opposite available
                for (int t = 0; t < 4; ++t) {
                    char d = cand[t];
                    if (canMove(d, r, c)) opts[cnt++] = d;
                }
            }
            char d = opts[rng.nextUInt(cnt)];
            path.push_back(d);
            if (d=='U') r--; else if (d=='D') r++; else if (d=='L') c--; else c++;
            last = d;
        }
        return path;
    }

    void applyPath(const string& path) {
        for (char d : path) {
            applyMove(board, zi, zj, d);
        }
        answer += path;
    }

    void solve() {
        // Initial metrics
        int curS = calcS(board);
        int curE = calcE(board);

        auto start = chrono::high_resolution_clock::now();
        const double TIME_LIMIT_MS = 1800.0;

        while ((int)answer.size() < Tlim) {
            auto now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double, std::milli>(now - start).count();
            if (elapsed > TIME_LIMIT_MS) break;

            bool improved = false;
            int Krem = Tlim - (int)answer.size();
            int maxL = min(20, Krem);
            if (maxL <= 0) break;

            int bestS = -1, bestE = -1;
            string bestPath;

            // Try multiple random paths, prefer short to long
            int totalTries = 300;
            for (int tries = 0; tries < totalTries; ++tries) {
                now = chrono::high_resolution_clock::now();
                elapsed = chrono::duration<double, std::milli>(now - start).count();
                if (elapsed > TIME_LIMIT_MS) break;

                int L = 1 + (int)(rng.nextUInt(maxL));
                string path = randomPath(L, zi, zj);
                vector<unsigned char> tb = board;
                int tr = zi, tc = zj;
                for (char d : path) applyMove(tb, tr, tc, d);
                int candS = calcS(tb);
                int candE = calcE(tb);

                if (candS > curS || (candS == curS && candE > curE)) {
                    if (candS > bestS || (candS == bestS && candE > bestE)) {
                        bestS = candS; bestE = candE; bestPath = path;
                        // If immediate improvement in S, we can early accept sometimes
                        if (candS > curS) {
                            // small chance to early accept
                            // But for simplicity, accept immediately
                            break;
                        }
                    }
                }
            }

            if (!bestPath.empty()) {
                applyPath(bestPath);
                curS = bestS;
                curE = bestE;
                improved = true;
            }

            if (!improved) {
                // Could not find improving move; stop
                break;
            }
        }
        // Output answer
        cout << answer << '\n';
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N; int Tlim;
    if (!(cin >> N >> Tlim)) {
        return 0;
    }
    vector<string> ts(N);
    for (int i = 0; i < N; ++i) cin >> ts[i];
    Solver solver;
    solver.N = N;
    solver.Tlim = Tlim;
    solver.n2 = N*N;
    solver.board.assign(N*N, 0);
    solver.zi = solver.zj = -1;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            char c = ts[i][j];
            if (c == '0') {
                solver.board[i*N + j] = 0;
                solver.zi = i; solver.zj = j;
            } else {
                solver.board[i*N + j] = (unsigned char)hexCharToInt(c);
            }
        }
    }
    if (solver.zi < 0) {
        // Fallback: ensure some empty (should not happen)
        solver.zi = N-1; solver.zj = N-1;
        solver.board[solver.zi* N + solver.zj] = 0;
    }
    solver.solve();
    return 0;
}