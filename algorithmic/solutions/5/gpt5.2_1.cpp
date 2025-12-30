#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
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

    inline void pushChar(char c) {
        if (idx == BUFSIZE) flush();
        buf[idx++] = c;
    }

    inline void writeInt(int x, char endc) {
        if (x == 0) {
            pushChar('0');
            pushChar(endc);
            return;
        }
        if (x < 0) {
            pushChar('-');
            x = -x;
        }
        char s[24];
        int n = 0;
        while (x) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        while (n--) pushChar(s[n]);
        pushChar(endc);
    }
};

static uint64_t rng_state = 88172645463325252ull;
static inline uint64_t nextRand() {
    rng_state ^= rng_state << 7;
    rng_state ^= rng_state >> 9;
    return rng_state;
}

struct CSR {
    int n;
    vector<int> start;
    vector<int> edges; // size = m
};

static inline int findBestNeighborOut(
    int u, int timer,
    const CSR &out,
    const vector<int> &deg,
    const vector<int> &vis
) {
    int best = -1;
    int bestScore = -1;
    for (int i = out.start[u]; i < out.start[u + 1]; ++i) {
        int v = out.edges[i];
        if (vis[v] == timer) continue;
        int sc = deg[v];
        if (sc > bestScore || (sc == bestScore && (nextRand() & 1))) {
            bestScore = sc;
            best = v;
        }
    }
    return best;
}

static inline int findBestNeighborIn(
    int u, int timer,
    const CSR &in,
    const vector<int> &deg,
    const vector<int> &vis
) {
    int best = -1;
    int bestScore = -1;
    for (int i = in.start[u]; i < in.start[u + 1]; ++i) {
        int v = in.edges[i]; // v -> u
        if (vis[v] == timer) continue;
        int sc = deg[v];
        if (sc > bestScore || (sc == bestScore && (nextRand() & 1))) {
            bestScore = sc;
            best = v;
        }
    }
    return best;
}

static inline void buildPathInBuffer(
    int startV, int timer, int n, int mid,
    vector<int> &buf, int &L, int &R,
    const CSR &out, const CSR &in,
    const vector<int> &deg,
    vector<int> &vis
) {
    L = R = mid;
    buf[L] = startV;
    vis[startV] = timer;

    bool backBlocked = false, frontBlocked = false;
    int storedBack = -1, storedFront = -1;
    int candBack = -2, candFront = -2;

    while (true) {
        int back = buf[R];
        int front = buf[L];

        if (!backBlocked) {
            if (storedBack != back || candBack == -2 || (candBack != -1 && vis[candBack] == timer)) {
                candBack = findBestNeighborOut(back, timer, out, deg, vis);
                storedBack = back;
            }
            if (candBack == -1) backBlocked = true;
        }

        if (!frontBlocked) {
            if (storedFront != front || candFront == -2 || (candFront != -1 && vis[candFront] == timer)) {
                candFront = findBestNeighborIn(front, timer, in, deg, vis);
                storedFront = front;
            }
            if (candFront == -1) frontBlocked = true;
        }

        if (backBlocked && frontBlocked) break;

        bool takeBack;
        if (frontBlocked) takeBack = true;
        else if (backBlocked) takeBack = false;
        else {
            int sb = deg[candBack];
            int sf = deg[candFront];
            if (sb > sf) takeBack = true;
            else if (sb < sf) takeBack = false;
            else takeBack = (nextRand() & 1);
        }

        if (takeBack) {
            int v = candBack;
            if (v == -1 || vis[v] == timer) {
                backBlocked = true;
                continue;
            }
            buf[++R] = v;
            vis[v] = timer;
            storedBack = -1;
            candBack = -2;
            backBlocked = false;
        } else {
            int v = candFront;
            if (v == -1 || vis[v] == timer) {
                frontBlocked = true;
                continue;
            }
            buf[--L] = v;
            vis[v] = timer;
            storedFront = -1;
            candFront = -2;
            frontBlocked = false;
        }

        if (R - L + 1 >= n) break;
    }
}

int main() {
    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    for (int i = 0; i < 10; ++i) {
        int tmp;
        fs.readInt(tmp);
    }

    vector<int> U(m), V(m);
    vector<int> outdeg(n + 2, 0), indeg(n + 2, 0);

    for (int i = 0; i < m; ++i) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        U[i] = u;
        V[i] = v;
        ++outdeg[u];
        ++indeg[v];
    }

    CSR out, in;
    out.n = in.n = n;
    out.start.assign(n + 2, 0);
    in.start.assign(n + 2, 0);

    for (int i = 1; i <= n; ++i) {
        out.start[i + 1] = out.start[i] + outdeg[i];
        in.start[i + 1] = in.start[i] + indeg[i];
    }

    out.edges.assign(m, 0);
    in.edges.assign(m, 0);

    vector<int> outCur = out.start;
    vector<int> inCur = in.start;
    for (int i = 0; i < m; ++i) {
        int u = U[i], v = V[i];
        out.edges[outCur[u]++] = v;
        in.edges[inCur[v]++] = u;
    }

    vector<int> deg(n + 2, 0);
    int maxOutV = 1, maxInV = 1, maxDegV = 1;
    for (int i = 1; i <= n; ++i) {
        deg[i] = outdeg[i] + indeg[i];
        if (outdeg[i] > outdeg[maxOutV]) maxOutV = i;
        if (indeg[i] > indeg[maxInV]) maxInV = i;
        if (deg[i] > deg[maxDegV]) maxDegV = i;
    }

    vector<int> starts;
    starts.reserve(32);
    unordered_set<int> used;
    used.reserve(64);

    auto addStart = [&](int x) {
        if (x < 1 || x > n) return;
        if (used.insert(x).second) starts.push_back(x);
    };

    addStart(1);
    addStart(maxDegV);
    addStart(maxOutV);
    addStart(maxInV);

    for (int i = 0; i < min(m, 5); ++i) {
        addStart(U[i]);
        addStart(V[i]);
    }
    for (int i = 0; i < 6; ++i) {
        int x = (int)(nextRand() % (uint64_t)n) + 1;
        addStart(x);
    }

    const int MAX_ATTEMPTS = 12;
    if ((int)starts.size() > MAX_ATTEMPTS) starts.resize(MAX_ATTEMPTS);

    vector<int> vis(n + 2, 0);
    int timer = 0;

    int mid = n + 5;
    vector<int> work(2 * n + 30, 0);
    vector<int> bestPath;
    bestPath.reserve(n);

    for (int s : starts) {
        ++timer;
        int L, R;
        buildPathInBuffer(s, timer, n, mid, work, L, R, out, in, deg, vis);
        int len = R - L + 1;
        if ((int)bestPath.size() < len) {
            bestPath.assign(work.begin() + L, work.begin() + R + 1);
            if ((int)bestPath.size() == n) break;
        }
    }

    if (bestPath.empty()) bestPath.push_back(1);

    FastOutput fo;
    fo.writeInt((int)bestPath.size(), '\n');
    for (int i = 0; i < (int)bestPath.size(); ++i) {
        fo.writeInt(bestPath[i], i + 1 == (int)bestPath.size() ? '\n' : ' ');
    }
    fo.flush();
    return 0;
}