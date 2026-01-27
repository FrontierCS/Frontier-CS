#include <iostream>
#include <vector>
#include <bitset>
#include <algorithm>
#include <random>
#include <string>
#include <numeric>

using namespace std;

const int MAXN = 2000;

vector<int> compute_colors(const vector<vector<int>>& adj, const vector<int>& deg, int iters) {
    int n = adj.size();
    vector<int> colors(n);
    for (int i = 0; i < n; ++i) colors[i] = deg[i];
    for (int it = 0; it < iters; ++it) {
        vector<string> keys(n);
        for (int v = 0; v < n; ++v) {
            vector<int> nb_colors;
            for (int u : adj[v]) nb_colors.push_back(colors[u]);
            sort(nb_colors.begin(), nb_colors.end());
            string key = to_string(colors[v]) + ":";
            for (int c : nb_colors) key += to_string(c) + ",";
            keys[v] = key;
        }
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(),
             [&](int a, int b) { return keys[a] < keys[b]; });
        vector<int> new_colors(n);
        int cur = 0;
        string prev = "";
        for (int idx : order) {
            if (keys[idx] != prev) {
                ++cur;
                prev = keys[idx];
            }
            new_colors[idx] = cur;
        }
        colors.swap(new_colors);
    }
    return colors;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    vector<bitset<MAXN>> adj1(n);
    vector<vector<int>> adj1_list(n);
    vector<int> deg1(n, 0);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj1[u].set(v);
        adj1[v].set(u);
        adj1_list[u].push_back(v);
        adj1_list[v].push_back(u);
        ++deg1[u];
        ++deg1[v];
    }

    vector<vector<int>> adj2_list(n);
    vector<int> deg2(n, 0);
    vector<pair<int, int>> edges2;
    edges2.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj2_list[u].push_back(v);
        adj2_list[v].push_back(u);
        ++deg2[u];
        ++deg2[v];
        edges2.emplace_back(u, v);
    }

    const int WL_ITERATIONS = 3;
    vector<int> color1 = compute_colors(adj1_list, deg1, WL_ITERATIONS);
    vector<int> color2 = compute_colors(adj2_list, deg2, WL_ITERATIONS);

    vector<int> sec1(n, 0), sec2(n, 0);
    for (int v = 0; v < n; ++v) {
        for (int u : adj1_list[v]) sec1[v] += deg1[u];
        for (int u : adj2_list[v]) sec2[v] += deg2[u];
    }

    vector<int> idx1(n), idx2(n);
    iota(idx1.begin(), idx1.end(), 0);
    iota(idx2.begin(), idx2.end(), 0);
    sort(idx1.begin(), idx1.end(), [&](int a, int b) {
        if (color1[a] != color1[b]) return color1[a] < color1[b];
        if (deg1[a] != deg1[b]) return deg1[a] < deg1[b];
        return sec1[a] < sec1[b];
    });
    sort(idx2.begin(), idx2.end(), [&](int a, int b) {
        if (color2[a] != color2[b]) return color2[a] < color2[b];
        if (deg2[a] != deg2[b]) return deg2[a] < deg2[b];
        return sec2[a] < sec2[b];
    });

    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        p[idx2[i]] = idx1[i];
    }

    int score = 0;
    for (const auto& e : edges2) {
        int u = e.first, v = e.second;
        if (adj1[p[u]][p[v]]) ++score;
    }

    auto compute_delta = [&](int i, int j) {
        int old_i = p[i], old_j = p[j];
        int delta = 0;
        for (int v : adj2_list[i]) {
            if (v == j) continue;
            bool old = adj1[old_i][p[v]];
            bool new_ = adj1[old_j][p[v]];
            delta += new_ - old;
        }
        for (int v : adj2_list[j]) {
            if (v == i) continue;
            bool old = adj1[old_j][p[v]];
            bool new_ = adj1[old_i][p[v]];
            delta += new_ - old;
        }
        return delta;
    };

    random_device rd;
    mt19937 gen(rd());
    uniform_int_distribution<int> dist(0, n-1);
    const int ITER = 50000;
    for (int iter = 0; iter < ITER; ++iter) {
        int i = dist(gen);
        int j = dist(gen);
        if (i == j) continue;
        int delta = compute_delta(i, j);
        if (delta > 0) {
            swap(p[i], p[j]);
            score += delta;
        }
    }

    for (int i = 0; i < n; ++i) {
        cout << p[i] + 1 << (i+1 == n ? "\n" : " ");
    }

    return 0;
}