#include <bits/stdc++.h>
using namespace std;

map<long long, pair<int, vector<int>>> memo;

pair<int, vector<int>> getPerm(long long k) {
    if (memo.count(k)) return memo[k];
    if (k == 1) return {0, {}};
    if (k == 2) return {1, {0}};
    if (k == 3) return {2, {1, 0}};
    
    int best_len = 1000; // large number
    vector<int> best_perm;
    
    // Try factorization into two numbers
    for (long long d = 2; d <= 1000 && d * d <= k; ++d) {
        if (k % d == 0) {
            auto [len1, perm1] = getPerm(d);
            auto [len2, perm2] = getPerm(k / d);
            int total_len = len1 + len2;
            if (total_len < best_len) {
                best_len = total_len;
                best_perm = perm1;
                int shift = len1;
                for (int x : perm2) best_perm.push_back(x + shift);
            }
        }
    }
    
    // If k is even: use the doubling construction (multiply by 2)
    if (k % 2 == 0) {
        auto [len_half, perm_half] = getPerm(k / 2);
        int total_len = len_half + 1;
        if (total_len < best_len) {
            best_len = total_len;
            best_perm.clear();
            best_perm.push_back(0);
            for (int x : perm_half) best_perm.push_back(x + 1);
        }
    }
    
    // If k is odd: use the double‑and‑add‑one construction
    if (k % 2 == 1) {
        auto [len_half, perm_half] = getPerm(k / 2);
        int total_len = len_half + 2;
        if (total_len < best_len) {
            best_len = total_len;
            // Build the even part: [0] + (perm_half shifted by 1)
            vector<int> even_part = {0};
            for (int x : perm_half) even_part.push_back(x + 1);
            // Prepend a new maximum element
            best_perm.clear();
            best_perm.push_back((int)even_part.size());
            for (int x : even_part) best_perm.push_back(x);
        }
    }
    
    return memo[k] = {best_len, best_perm};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int q;
    cin >> q;
    vector<long long> ks(q);
    for (int i = 0; i < q; ++i) cin >> ks[i];
    
    for (long long k : ks) {
        auto [n, perm] = getPerm(k);
        cout << n << "\n";
        for (int i = 0; i < n; ++i) {
            cout << perm[i] << (i+1 < n ? " " : "\n");
        }
    }
    
    return 0;
}