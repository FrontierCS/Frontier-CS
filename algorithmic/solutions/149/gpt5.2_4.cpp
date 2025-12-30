#include <bits/stdc++.h>
using namespace std;

struct XorShift64 {
    uint64_t x;
    explicit XorShift64(uint64_t seed = 88172645463325252ull) : x(seed) {}
    uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    int nextInt(int lo, int hi) { // inclusive
        return lo + (int)(nextU64() % (uint64_t)(hi - lo + 1));
    }
    double nextDouble() { // [0,1)
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

struct Adj {
    int to;
    int idx;
    char mv;
};

static constexpr int N = 30;
static constexpr int V = N * N;
static constexpr int EH = N * (N - 1);
static constexpr int EV = (N - 1) * N;
static constexpr int E = EH + EV;

struct Solver {
    vector<vector<Adj>> g;
    vector<double> w;
    vector<int> cnt;
    int hid[N][N-1];
    int vid[N-1][N];
    XorShift64 rng;

    Solver() : g(V), w(E, 5000.0), cnt(E, 0) {
        uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
        seed ^= (uint64_t)(uintptr_t)this;
        rng = XorShift64(seed);

        int idx = 0;
        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N - 1; j++) hid[i][j] = idx++;
        }
        for (int i = 0; i < N - 1; i++) {
            for (int j = 0; j < N; j++) vid[i][j] = idx++;
        }

        for (int i = 0; i < N; i++) {
            for (int j = 0; j < N; j++) {
                int u = i * N + j;
                if (j + 1 < N) {
                    int v = i * N + (j + 1);
                    int eidx = hid[i][j];
                    g[u].push_back({v, eidx, 'R'});
                    g[v].push_back({u, eidx, 'L'});
                }
                if (i + 1 < N) {
                    int v = (i + 1) * N + j;
                    int eidx = vid[i][j];
                    g[u].push_back({v, eidx, 'D'});
                    g[v].push_back({u, eidx, 'U'});
                }
            }
        }
    }

    inline int edgeIndexFromMove(int i, int j, char mv) const {
        if (mv == 'R') return hid[i][j];
        if (mv == 'L') return hid[i][j - 1];
        if (mv == 'D') return vid[i][j];
        return vid[i - 1][j]; // 'U'
    }

    bool simulateEdges(int si, int sj, const string& path, vector<int>& edges) const {
        edges.clear();
        edges.reserve(path.size());
        int i = si, j = sj;
        vector<unsigned char> vis(V, 0);
        vis[i * N + j] = 1;
        for (char c : path) {
            int ni = i, nj = j;
            if (c == 'U') ni--;
            else if (c == 'D') ni++;
            else if (c == 'L') nj--;
            else if (c == 'R') nj++;
            else return false;
            if (ni < 0 || ni >= N || nj < 0 || nj >= N) return false;
            int vtx = ni * N + nj;
            if (vis[vtx]) return false;
            vis[vtx] = 1;
            int eidx = edgeIndexFromMove(i, j, c);
            edges.push_back(eidx);
            i = ni; j = nj;
        }
        return true;
    }

    string manhattanPath(int si, int sj, int ti, int tj, bool hvOrder) {
        string res;
        res.reserve(abs(si - ti) + abs(sj - tj));
        int i = si, j = sj;
        auto doV = [&]() {
            while (i < ti) { res.push_back('D'); i++; }
            while (i > ti) { res.push_back('U'); i--; }
        };
        auto doH = [&]() {
            while (j < tj) { res.push_back('R'); j++; }
            while (j > tj) { res.push_back('L'); j--; }
        };
        if (hvOrder) { doH(); doV(); }
        else { doV(); doH(); }
        return res;
    }

    string dijkstraPath(int si, int sj, int ti, int tj) {
        int s = si * N + sj;
        int t = ti * N + tj;
        const double INF = 1e100;

        vector<double> dist(V, INF);
        vector<int> prev(V, -1), prevE(V, -1);
        vector<char> prevM(V, 0);

        priority_queue<pair<double,int>, vector<pair<double,int>>, greater<pair<double,int>>> pq;
        dist[s] = 0.0;
        pq.push({0.0, s});

        while (!pq.empty()) {
            auto [d, u] = pq.top();
            pq.pop();
            if (d != dist[u]) continue;
            if (u == t) break;
            for (const auto& e : g[u]) {
                double nd = d + w[e.idx];
                if (nd < dist[e.to]) {
                    dist[e.to] = nd;
                    prev[e.to] = u;
                    prevE[e.to] = e.idx;
                    prevM[e.to] = e.mv;
                    pq.push({nd, e.to});
                }
            }
        }

        if (prev[t] == -1) return "";

        string path;
        int cur = t;
        while (cur != s) {
            char mv = prevM[cur];
            if (!mv) return "";
            path.push_back(mv);
            cur = prev[cur];
        }
        reverse(path.begin(), path.end());
        return path;
    }

    string getPath(int k, int si, int sj, int ti, int tj) {
        int man = abs(si - ti) + abs(sj - tj);

        if (k < 200) {
            bool hvOrder = (rng.nextU64() & 1ULL);
            return manhattanPath(si, sj, ti, tj, hvOrder);
        }

        string path = dijkstraPath(si, sj, ti, tj);
        if (path.empty()) {
            return manhattanPath(si, sj, ti, tj, false);
        }

        if ((int)path.size() > max(3 * man, man + 40)) {
            bool hvOrder = (rng.nextU64() & 1ULL);
            return manhattanPath(si, sj, ti, tj, hvOrder);
        }

        vector<int> edges;
        if (!simulateEdges(si, sj, path, edges)) {
            bool hvOrder = (rng.nextU64() & 1ULL);
            return manhattanPath(si, sj, ti, tj, hvOrder);
        }
        int endi = si, endj = sj;
        for (char c : path) {
            if (c == 'U') endi--;
            else if (c == 'D') endi++;
            else if (c == 'L') endj--;
            else if (c == 'R') endj++;
        }
        if (endi != ti || endj != tj) {
            bool hvOrder = (rng.nextU64() & 1ULL);
            return manhattanPath(si, sj, ti, tj, hvOrder);
        }
        return path;
    }

    void updateFromFeedback(int si, int sj, const string& path, long long feedback) {
        vector<int> edges;
        if (!simulateEdges(si, sj, path, edges)) return;

        double sumEst = 0.0;
        for (int idx : edges) sumEst += w[idx];
        if (!(sumEst > 0)) return;

        double ratio = (double)feedback / sumEst;
        if (ratio < 0.5) ratio = 0.5;
        if (ratio > 1.8) ratio = 1.8;

        const double alpha = 0.65;

        for (int idx : edges) {
            cnt[idx]++;
            double beta = alpha / sqrt((double)cnt[idx]);
            if (beta > 0.8) beta = 0.8;
            double mult = (1.0 - beta) + beta * ratio;
            w[idx] *= mult;
            if (w[idx] < 500.0) w[idx] = 500.0;
            if (w[idx] > 9500.0) w[idx] = 9500.0;
        }
    }
};

static long long round_ll(double x) {
    return (long long)llround(x);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string line;
    while (true) {
        if (!getline(cin, line)) return 0;
        if (!line.empty()) break;
    }
    stringstream ss(line);
    vector<long long> first;
    {
        long long x;
        while (ss >> x) first.push_back(x);
    }

    Solver solver;

    // Offline mode detection: first line has 29 ints (h row)
    if ((int)first.size() == 29) {
        vector<vector<int>> h(N, vector<int>(N - 1));
        vector<vector<int>> v(N - 1, vector<int>(N));

        for (int j = 0; j < N - 1; j++) h[0][j] = (int)first[j];
        for (int i = 1; i < N; i++) {
            for (int j = 0; j < N - 1; j++) cin >> h[i][j];
        }
        for (int i = 0; i < N - 1; i++) {
            for (int j = 0; j < N; j++) cin >> v[i][j];
        }

        for (int k = 0; k < 1000; k++) {
            int si, sj, ti, tj;
            long long a_dummy;
            double e;
            if (!(cin >> si >> sj >> ti >> tj >> a_dummy >> e)) break;

            string path = solver.getPath(k, si, sj, ti, tj);
            cout << path << "\n";

            long long b = 0;
            int i = si, j = sj;
            vector<unsigned char> vis(V, 0);
            vis[i * N + j] = 1;
            bool ok = true;
            for (char c : path) {
                if (c == 'R') { b += h[i][j]; j++; }
                else if (c == 'L') { b += h[i][j - 1]; j--; }
                else if (c == 'D') { b += v[i][j]; i++; }
                else if (c == 'U') { b += v[i - 1][j]; i--; }
                else { ok = false; break; }
                if (i < 0 || i >= N || j < 0 || j >= N) { ok = false; break; }
                int id = i * N + j;
                if (vis[id]) { ok = false; break; }
                vis[id] = 1;
            }
            if (!ok) continue;

            long long feedback = round_ll((double)b * e);
            solver.updateFromFeedback(si, sj, path, feedback);
        }
        return 0;
    }

    // Interactive mode: first line is first query (4 ints)
    if ((int)first.size() != 4) return 0;

    for (int k = 0; k < 1000; k++) {
        int si, sj, ti, tj;
        if (k == 0) {
            si = (int)first[0];
            sj = (int)first[1];
            ti = (int)first[2];
            tj = (int)first[3];
        } else {
            if (!(cin >> si >> sj >> ti >> tj)) break;
        }

        string path = solver.getPath(k, si, sj, ti, tj);
        cout << path << '\n';
        cout.flush();

        long long feedback;
        if (!(cin >> feedback)) break;
        solver.updateFromFeedback(si, sj, path, feedback);
    }

    return 0;
}