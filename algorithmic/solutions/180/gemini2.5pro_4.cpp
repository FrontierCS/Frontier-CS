#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <chrono>
#include <random>

using namespace std;

const int MAXN = 2001;
int n, m;
vector<int> adj1[MAXN], adj2[MAXN];
bool adj1_mat[MAXN][MAXN];

vector<long long> colors1, colors2;

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

void compute_wl() {
    colors1.assign(n + 1, 0);
    colors2.assign(n + 1, 0);

    vector<int> degrees;
    degrees.reserve(2 * n);
    for (int i = 1; i <= n; ++i) {
        degrees.push_back(adj1[i].size());
    }
    for (int i = 1; i <= n; ++i) {
        degrees.push_back(adj2[i].size());
    }
    sort(degrees.begin(), degrees.end());
    degrees.erase(unique(degrees.begin(), degrees.end()), degrees.end());

    for (int i = 1; i <= n; ++i) {
        colors1[i] = lower_bound(degrees.begin(), degrees.end(), adj1[i].size()) - degrees.begin();
        colors2[i] = lower_bound(degrees.begin(), degrees.end(), adj2[i].size()) - degrees.begin();
    }

    int num_iterations = 12;
    long long prev_num_colors = 0;

    uniform_int_distribution<long long> dist(1'000'000'007LL, 2'000'000'000LL);
    long long A = dist(rng), B = dist(rng);
    long long C = dist(rng), D = dist(rng);
    long long M1 = 1'000'000'007LL, M2 = 1'000'000'009LL;

    vector<long long> p_powers1(2 * n + 1), p_powers2(2 * n + 1);
    p_powers1[0] = 1;
    p_powers2[0] = 1;
    for (int i = 1; i <= 2 * n; ++i) {
        p_powers1[i] = (p_powers1[i - 1] * B) % M1;
        p_powers2[i] = (p_powers2[i - 1] * D) % M2;
    }
    
    for (int iter = 0; iter < num_iterations; ++iter) {
        vector<pair<long long, long long>> next_hashes1(n + 1), next_hashes2(n + 1);
        vector<pair<long long, long long>> all_hashes;
        all_hashes.reserve(2 * n);

        for (int i = 1; i <= n; ++i) {
            long long h1 = 0, h2 = 0;
            for (int neighbor : adj1[i]) {
                h1 = (h1 + p_powers1[colors1[neighbor]]) % M1;
                h2 = (h2 + p_powers2[colors1[neighbor]]) % M2;
            }
            next_hashes1[i] = {(colors1[i] * A + h1) % M1, (colors1[i] * C + h2) % M2};
            all_hashes.push_back(next_hashes1[i]);
        }
        for (int i = 1; i <= n; ++i) {
            long long h1 = 0, h2 = 0;
            for (int neighbor : adj2[i]) {
                h1 = (h1 + p_powers1[colors2[neighbor]]) % M1;
                h2 = (h2 + p_powers2[colors2[neighbor]]) % M2;
            }
            next_hashes2[i] = {(colors2[i] * A + h1) % M1, (colors2[i] * C + h2) % M2};
            all_hashes.push_back(next_hashes2[i]);
        }
        
        sort(all_hashes.begin(), all_hashes.end());
        all_hashes.erase(unique(all_hashes.begin(), all_hashes.end()), all_hashes.end());
        
        for (int i = 1; i <= n; ++i) {
            colors1[i] = lower_bound(all_hashes.begin(), all_hashes.end(), next_hashes1[i]) - all_hashes.begin();
            colors2[i] = lower_bound(all_hashes.begin(), all_hashes.end(), next_hashes2[i]) - all_hashes.begin();
        }

        if (all_hashes.size() == prev_num_colors) {
            break;
        }
        prev_num_colors = all_hashes.size();
    }
}

void local_search(vector<int>& p) {
    long long max_color = 0;
    for (int i = 1; i <= n; ++i) {
        max_color = max(max_color, colors2[i]);
    }

    vector<vector<int>> g2_by_color(max_color + 1);
    for (int i = 1; i <= n; ++i) {
        g2_by_color[colors2[i]].push_back(i);
    }
    
    vector<int> non_trivial_groups;
    for (size_t i = 0; i < g2_by_color.size(); ++i) {
        if (g2_by_color[i].size() > 1) {
            non_trivial_groups.push_back(i);
        }
    }

    if (non_trivial_groups.empty()) {
        return;
    }

    int num_iterations = 40 * n;
    if (n > 1000) num_iterations = 20 * n;
    
    for (int iter = 0; iter < num_iterations; ++iter) {
        uniform_int_distribution<int> group_dist(0, non_trivial_groups.size() - 1);
        int group_idx = group_dist(rng);
        int color_id = non_trivial_groups[group_idx];

        const auto& group = g2_by_color[color_id];
        uniform_int_distribution<int> node_dist(0, group.size() - 1);
        int u_idx = node_dist(rng);
        int v_idx;
        do {
            v_idx = node_dist(rng);
        } while (u_idx == v_idx);

        int u = group[u_idx];
        int v = group[v_idx];
        
        int p_u = p[u], p_v = p[v];
        
        int delta = 0;
        for (int neighbor : adj2[u]) {
            if (neighbor == v) continue;
            delta += adj1_mat[p_v][p[neighbor]] - adj1_mat[p_u][p[neighbor]];
        }
        for (int neighbor : adj2[v]) {
            if (neighbor == u) continue;
            delta += adj1_mat[p_u][p[neighbor]] - adj1_mat[p_v][p[neighbor]];
        }

        if (delta > 0) {
            swap(p[u], p[v]);
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m;

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
        adj1_mat[u][v] = adj1_mat[v][u] = true;
    }

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
    }

    compute_wl();
    
    vector<pair<long long, int>> sorted_v1, sorted_v2;
    sorted_v1.reserve(n);
    sorted_v2.reserve(n);
    for (int i = 1; i <= n; ++i) {
        sorted_v1.push_back({colors1[i], i});
        sorted_v2.push_back({colors2[i], i});
    }

    sort(sorted_v1.begin(), sorted_v1.end());
    sort(sorted_v2.begin(), sorted_v2.end());

    vector<int> p(n + 1);
    for (int i = 0; i < n; ++i) {
        p[sorted_v2[i].second] = sorted_v1[i].second;
    }
    
    local_search(p);
    
    for (int i = 1; i <= n; ++i) {
        cout << p[i] << (i == n ? "" : " ");
    }
    cout << endl;

    return 0;
}