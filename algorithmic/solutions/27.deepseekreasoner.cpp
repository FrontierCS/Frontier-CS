#include <bits/stdc++.h>
using namespace std;

bool is_prime(int x) {
    if (x < 2) return false;
    for (int i = 2; i * i <= x; i++) {
        if (x % i == 0) return false;
    }
    return true;
}

struct EdgeInfo {
    int r, c, v;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n, m;
    cin >> n >> m;
    if (n == 1 || m == 1) {
        int k = n * m;
        cout << k << '\n';
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= m; j++) {
                cout << i << ' ' << j << '\n';
            }
        }
        return 0;
    }
    
    int maxval = max(n, m);
    int p = ceil(sqrt(maxval + 1));
    while (!is_prime(p)) p++;
    
    vector<pair<int,int>> all_pairs;
    for (int a = 0; a < p; a++) {
        for (int b = 0; b < p; b++) {
            if (a == 0 && b == 0) continue;
            all_pairs.emplace_back(a, b);
        }
    }
    
    const int TRIALS = 50;
    int best_count = 0;
    vector<pair<int,int>> best_edges;
    
    // Deterministic trial
    {
        vector<pair<int,int>> row_pairs(all_pairs.begin(), all_pairs.begin() + n);
        vector<pair<int,int>> col_pairs(all_pairs.begin(), all_pairs.begin() + m);
        vector<int> cnt(p, 0);
        vector<EdgeInfo> edge_data;
        edge_data.reserve(n * m);
        for (int i = 0; i < n; i++) {
            int a = row_pairs[i].first, b = row_pairs[i].second;
            for (int j = 0; j < m; j++) {
                int x = col_pairs[j].first, y = col_pairs[j].second;
                int v = (a * x + b * y) % p;
                if (v != 0) {
                    edge_data.push_back({i+1, j+1, v});
                    cnt[v]++;
                }
            }
        }
        int best_c = 1;
        for (int c = 2; c < p; c++) {
            if (cnt[c] > cnt[best_c]) best_c = c;
        }
        int count = cnt[best_c];
        if (count > best_count) {
            best_count = count;
            best_edges.clear();
            for (auto &e : edge_data) {
                if (e.v == best_c) {
                    best_edges.emplace_back(e.r, e.c);
                }
            }
        }
    }
    
    random_device rd;
    mt19937 g(rd());
    
    for (int trial = 1; trial < TRIALS; trial++) {
        shuffle(all_pairs.begin(), all_pairs.end(), g);
        vector<pair<int,int>> row_pairs(all_pairs.begin(), all_pairs.begin() + n);
        shuffle(all_pairs.begin(), all_pairs.end(), g);
        vector<pair<int,int>> col_pairs(all_pairs.begin(), all_pairs.begin() + m);
        
        vector<int> cnt(p, 0);
        vector<EdgeInfo> edge_data;
        edge_data.reserve(n * m);
        for (int i = 0; i < n; i++) {
            int a = row_pairs[i].first, b = row_pairs[i].second;
            for (int j = 0; j < m; j++) {
                int x = col_pairs[j].first, y = col_pairs[j].second;
                int v = (a * x + b * y) % p;
                if (v != 0) {
                    edge_data.push_back({i+1, j+1, v});
                    cnt[v]++;
                }
            }
        }
        int best_c = 1;
        for (int c = 2; c < p; c++) {
            if (cnt[c] > cnt[best_c]) best_c = c;
        }
        int count = cnt[best_c];
        if (count > best_count) {
            best_count = count;
            best_edges.clear();
            for (auto &e : edge_data) {
                if (e.v == best_c) {
                    best_edges.emplace_back(e.r, e.c);
                }
            }
        }
    }
    
    cout << best_count << '\n';
    for (auto &e : best_edges) {
        cout << e.first << ' ' << e.second << '\n';
    }
    
    return 0;
}