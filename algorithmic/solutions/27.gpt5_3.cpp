#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    
    vector<pair<int,int>> edges;
    
    // Trivial cases: one dimension is 1
    if (n == 1) {
        for (int c = 1; c <= m; ++c) edges.emplace_back(1, c);
        cout << edges.size() << "\n";
        for (auto &e : edges) cout << e.first << " " << e.second << "\n";
        return 0;
    }
    if (m == 1) {
        for (int r = 1; r <= n; ++r) edges.emplace_back(r, 1);
        cout << edges.size() << "\n";
        for (auto &e : edges) cout << e.first << " " << e.second << "\n";
        return 0;
    }
    // Special handling when one side is 2 to get near-optimal simple construction
    if (n == 2) {
        for (int c = 1; c <= m; ++c) {
            int r = (c % 2) + 1;
            edges.emplace_back(r, c);
        }
        // Add one more cell in column 1 for the other row
        if (m >= 1) {
            int existing_row = (1 % 2) + 1; // For c=1
            int other_row = (existing_row == 1 ? 2 : 1);
            edges.emplace_back(other_row, 1);
        }
        cout << edges.size() << "\n";
        for (auto &e : edges) cout << e.first << " " << e.second << "\n";
        return 0;
    }
    if (m == 2) {
        for (int r = 1; r <= n; ++r) {
            int c = (r % 2) + 1;
            edges.emplace_back(r, c);
        }
        // Add one more cell in row 1 for the other column
        if (n >= 1) {
            int existing_col = (1 % 2) + 1; // For r=1
            int other_col = (existing_col == 1 ? 2 : 1);
            edges.emplace_back(1, other_col);
        }
        cout << edges.size() << "\n";
        for (auto &e : edges) cout << e.first << " " << e.second << "\n";
        return 0;
    }
    
    // General construction: C4-free bipartite graph by preventing duplicate pairs
    long long NM = 1LL * n * m;
    long long K = min(300000LL, 2 * NM); // pair budget to limit memory/time
    
    auto inverse_choose_limit = [](long long limit) -> int {
        if (limit <= 0) return 1;
        long double t = (long double)limit;
        long double L = floor((1.0L + sqrt(1.0L + 8.0L * t)) / 2.0L);
        if (L < 1) L = 1;
        if (L > (long double)2e9) L = (long double)2e9;
        return (int)L;
    };
    
    // Compute degree caps based on pair budget
    int Lc = inverse_choose_limit(K / max(1, m)); // per column degree cap
    if (Lc > n) Lc = n;
    if (Lc < 1) Lc = 1;
    int Lr = inverse_choose_limit(K / max(1, n)); // per row degree cap
    if (Lr > m) Lr = m;
    if (Lr < 1) Lr = 1;
    
    // Decide orientation by potential capacity
    long long potRowPairs = 1LL * m * Lc; // if tracking row pairs (limit per column)
    long long potColPairs = 1LL * n * Lr; // if tracking column pairs (limit per row)
    
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    
    if (potRowPairs >= potColPairs) {
        // Track pairs of rows: ensure no two rows share two columns.
        // Limit per-column degree to Lc.
        vector<vector<int>> colAdj(m);
        for (int c = 0; c < m; ++c) colAdj[c].reserve(Lc);
        unordered_set<uint64_t> pairSet;
        pairSet.reserve((size_t)min<long long>(K, 400000));
        pairSet.max_load_factor(0.7f);
        
        vector<int> rowPerm(n), colPerm(m);
        iota(rowPerm.begin(), rowPerm.end(), 0);
        iota(colPerm.begin(), colPerm.end(), 0);
        
        int maxPass = 3;
        size_t prevE = 0;
        for (int pass = 0; pass < maxPass; ++pass) {
            shuffle(rowPerm.begin(), rowPerm.end(), rng);
            shuffle(colPerm.begin(), colPerm.end(), rng);
            size_t addedThisPass = 0;
            for (int idxc = 0; idxc < m; ++idxc) {
                int c = colPerm[idxc];
                if ((int)colAdj[c].size() >= Lc) continue;
                int shift = n > 1 ? (int)(rng() % n) : 0;
                for (int j = 0; j < n && (int)colAdj[c].size() < Lc; ++j) {
                    int r = rowPerm[(j + shift) % n];
                    // check duplicate in this column
                    bool exists = false;
                    for (int rr : colAdj[c]) {
                        if (rr == r) { exists = true; break; }
                    }
                    if (exists) continue;
                    // check row pair collisions
                    bool ok = true;
                    for (int rr : colAdj[c]) {
                        int a = rr, b = r;
                        if (a > b) swap(a, b);
                        uint64_t key = (uint64_t)a * (uint64_t)n + (uint64_t)b;
                        if (pairSet.find(key) != pairSet.end()) { ok = false; break; }
                    }
                    if (!ok) continue;
                    // add edge
                    for (int rr : colAdj[c]) {
                        int a = rr, b = r;
                        if (a > b) swap(a, b);
                        uint64_t key = (uint64_t)a * (uint64_t)n + (uint64_t)b;
                        pairSet.insert(key);
                    }
                    colAdj[c].push_back(r);
                    edges.emplace_back(r + 1, c + 1);
                    ++addedThisPass;
                }
            }
            if (edges.size() == prevE || addedThisPass == 0) break;
            prevE = edges.size();
        }
    } else {
        // Track pairs of columns: ensure no two columns share two rows.
        // Limit per-row degree to Lr.
        vector<vector<int>> rowAdj(n);
        for (int r = 0; r < n; ++r) rowAdj[r].reserve(Lr);
        unordered_set<uint64_t> pairSet;
        pairSet.reserve((size_t)min<long long>(K, 400000));
        pairSet.max_load_factor(0.7f);
        
        vector<int> rowPerm(n), colPerm(m);
        iota(rowPerm.begin(), rowPerm.end(), 0);
        iota(colPerm.begin(), colPerm.end(), 0);
        
        int maxPass = 3;
        size_t prevE = 0;
        for (int pass = 0; pass < maxPass; ++pass) {
            shuffle(rowPerm.begin(), rowPerm.end(), rng);
            shuffle(colPerm.begin(), colPerm.end(), rng);
            size_t addedThisPass = 0;
            for (int idxr = 0; idxr < n; ++idxr) {
                int r = rowPerm[idxr];
                if ((int)rowAdj[r].size() >= Lr) continue;
                int shift = m > 1 ? (int)(rng() % m) : 0;
                for (int j = 0; j < m && (int)rowAdj[r].size() < Lr; ++j) {
                    int c = colPerm[(j + shift) % m];
                    // check duplicate in this row
                    bool exists = false;
                    for (int cc : rowAdj[r]) {
                        if (cc == c) { exists = true; break; }
                    }
                    if (exists) continue;
                    // check column pair collisions
                    bool ok = true;
                    for (int cc : rowAdj[r]) {
                        int a = cc, b = c;
                        if (a > b) swap(a, b);
                        uint64_t key = (uint64_t)a * (uint64_t)m + (uint64_t)b;
                        if (pairSet.find(key) != pairSet.end()) { ok = false; break; }
                    }
                    if (!ok) continue;
                    // add edge
                    for (int cc : rowAdj[r]) {
                        int a = cc, b = c;
                        if (a > b) swap(a, b);
                        uint64_t key = (uint64_t	a) * (uint64_t)m + (uint64_t)b;
                        pairSet.insert(key);
                    }
                    rowAdj[r].push_back(c);
                    edges.emplace_back(r + 1, c + 1);
                    ++addedThisPass;
                }
            }
            if (edges.size() == prevE || addedThisPass == 0) break;
            prevE = edges.size();
        }
    }
    
    cout << edges.size() << "\n";
    for (auto &e : edges) cout << e.first << " " << e.second << "\n";
    return 0;
}