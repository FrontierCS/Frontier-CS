#include <bits/stdc++.h>
using namespace std;

static constexpr int N = 30;
static constexpr int V = N * N;

struct EdgeRef {
    bool horiz; // true: h[i][j], false: v[i][j]
    int i, j;
};

static inline int vid(int i, int j) { return i * N + j; }

struct DijkstraResult {
    string path;
    double predicted;
    vector<EdgeRef> edges;
};

DijkstraResult solve_path(int si, int sj, int ti, int tj,
                          const array<array<double, N - 1>, N>& h,
                          const array<array<double, N>, N - 1>& v) {
    const int s = vid(si, sj);
    const int t = vid(ti, tj);

    array<double, V> dist;
    dist.fill(1e100);
    array<int, V> prev;
    prev.fill(-1);
    array<char, V> prev_dir;
    prev_dir.fill('?');

    using P = pair<double, int>;
    priority_queue<P, vector<P>, greater<P>> pq;
    dist[s] = 0.0;
    pq.push({0.0, s});

    auto relax = [&](int from, int to, double w, char dir) {
        double nd = dist[from] + w;
        if (nd < dist[to]) {
            dist[to] = nd;
            prev[to] = from;
            prev_dir[to] = dir;
            pq.push({nd, to});
        }
    };

    while (!pq.empty()) {
        auto [d, x] = pq.top();
        pq.pop();
        if (d != dist[x]) continue;
        if (x == t) break;
        int i = x / N, j = x % N;

        if (i > 0) relax(x, vid(i - 1, j), v[i - 1][j], 'U');
        if (i + 1 < N) relax(x, vid(i + 1, j), v[i][j], 'D');
        if (j > 0) relax(x, vid(i, j - 1), h[i][j - 1], 'L');
        if (j + 1 < N) relax(x, vid(i, j + 1), h[i][j], 'R');
    }

    string path;
    {
        int cur = t;
        while (cur != s) {
            int p = prev[cur];
            if (p < 0) break; // should not happen in grid
            path.push_back(prev_dir[cur]);
            cur = p;
        }
        reverse(path.begin(), path.end());
    }

    vector<EdgeRef> edges;
    edges.reserve(path.size());
    int ci = si, cj = sj;
    double predicted = 0.0;
    for (char c : path) {
        if (c == 'R') {
            edges.push_back({true, ci, cj});
            predicted += h[ci][cj];
            cj++;
        } else if (c == 'L') {
            edges.push_back({true, ci, cj - 1});
            predicted += h[ci][cj - 1];
            cj--;
        } else if (c == 'D') {
            edges.push_back({false, ci, cj});
            predicted += v[ci][cj];
            ci++;
        } else if (c == 'U') {
            edges.push_back({false, ci - 1, cj});
            predicted += v[ci - 1][cj];
            ci--;
        }
    }

    return {path, predicted, edges};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long firstLL;
    if (!(cin >> firstLL)) return 0;

    // If first token is an edge length (>= 1000 roughly), assume offline format with full h/v and queries.
    bool offline = (firstLL > 29);

    array<array<double, N - 1>, N> h{};
    array<array<double, N>, N - 1> v{};

    if (offline) {
        // Read full h and v
        h[0][0] = (double)firstLL;
        for (int j = 1; j < N - 1; j++) cin >> h[0][j];
        for (int i = 1; i < N; i++) {
            for (int j = 0; j < N - 1; j++) cin >> h[i][j];
        }
        for (int i = 0; i < N - 1; i++) {
            for (int j = 0; j < N; j++) cin >> v[i][j];
        }

        for (int k = 0; k < 1000; k++) {
            int si, sj, ti, tj;
            if (!(cin >> si >> sj >> ti >> tj)) break;
            long long a;
            double e;
            if (!(cin >> a >> e)) { a = 0; e = 1.0; }
            auto res = solve_path(si, sj, ti, tj, h, v);
            cout << res.path << "\n";
        }
        return 0;
    }

    // Interactive-like mode: no true weights given, learn online.
    // Initialize with a reasonable constant.
    for (int i = 0; i < N; i++) for (int j = 0; j < N - 1; j++) h[i][j] = 5000.0;
    for (int i = 0; i < N - 1; i++) for (int j = 0; j < N; j++) v[i][j] = 5000.0;

    int si = (int)firstLL, sj, ti, tj;
    cin >> sj >> ti >> tj;

    long long observed = 0;
    for (int k = 0; k < 1000; k++) {
        auto res = solve_path(si, sj, ti, tj, h, v);

        cout << res.path << "\n" << flush;

        if (!(cin >> observed)) break;

        // Update estimates along used edges.
        const double pred = max(1.0, res.predicted);
        const double obs = (double)observed;
        const int m = (int)res.edges.size();
        if (m > 0) {
            // Additive correction distributed across edges.
            const double lr = (k < 50 ? 0.5 : 0.25);
            double delta = lr * (obs - pred) / (double)m;

            auto clamp_w = [](double x) {
                if (x < 100.0) x = 100.0;
                if (x > 10000.0) x = 10000.0;
                return x;
            };

            for (const auto &er : res.edges) {
                if (er.horiz) {
                    h[er.i][er.j] = clamp_w(h[er.i][er.j] + delta);
                } else {
                    v[er.i][er.j] = clamp_w(v[er.i][er.j] + delta);
                }
            }
        }

        if (k + 1 == 1000) break;
        cin >> si >> sj >> ti >> tj;
    }

    return 0;
}