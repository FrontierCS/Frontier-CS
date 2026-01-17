#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    cin >> N;
    vector<int> S(N);
    for (auto &x : S) cin >> x;
    int M;
    cin >> M;
    vector<pair<int, int>> jerry(M);
    for (auto &[x, y] : jerry) cin >> x >> y;
    
    vector<int> value_at = S;
    vector<int> position_of(N);
    for (int i = 0; i < N; i++) position_of[S[i]] = i;
    set<int> wrongs;
    for (int i = 0; i < N; i++) if (value_at[i] != i) wrongs.insert(i);
    
    long long best_v = LLONG_MAX / 2;
    int best_r = -1;
    if (wrongs.empty()) {
        best_v = 0;
        best_r = 0;
    }
    
    vector<long long> cum_sum(M + 1, 0);
    vector<bool> is_sorted_after(M + 1, false);
    is_sorted_after[0] = wrongs.empty();
    cum_sum[0] = 0;
    
    long long current_sum = 0;
    for (int r = 1; r <= M; r++) {
        // Jerry's swap
        auto [x, y] = jerry[r - 1];
        if (x != y) {
            int valx = value_at[x];
            int valy = value_at[y];
            value_at[x] = valy;
            value_at[y] = valx;
            position_of[valx] = y;
            position_of[valy] = x;
            wrongs.erase(x);
            wrongs.erase(y);
            if (value_at[x] != x) wrongs.insert(x);
            if (value_at[y] != y) wrongs.insert(y);
        }
        
        // My swap
        int uk = 0, vk = 0;
        long long this_cost = 0;
        if (!wrongs.empty()) {
            int i = *wrongs.begin();
            int p = position_of[i];
            if (p != i) {
                uk = i;
                vk = p;
                this_cost = abs(uk - vk);
                // Perform swap
                int valu = value_at[uk];
                int valv = value_at[vk];
                value_at[uk] = valv;
                value_at[vk] = valu;
                position_of[valu] = vk;
                position_of[valv] = uk;
                wrongs.erase(uk);
                wrongs.erase(vk);
                if (value_at[uk] != uk) wrongs.insert(uk);
                if (value_at[vk] != vk) wrongs.insert(vk);
            }
        }
        current_sum += this_cost;
        cum_sum[r] = current_sum;
        is_sorted_after[r] = wrongs.empty();
        
        if (is_sorted_after[r]) {
            long long v = (long long) r * current_sum;
            if (v < best_v) {
                best_v = v;
                best_r = r;
            }
        }
    }
    
    // Now second simulation to record swaps
    if (best_r == 0) {
        cout << 0 << '\n';
        cout << 0 << '\n';
        return 0;
    }
    
    // Reset
    value_at = S;
    for (int i = 0; i < N; i++) position_of[S[i]] = i;
    wrongs.clear();
    for (int i = 0; i < N; i++) if (value_at[i] != i) wrongs.insert(i);
    
    vector<pair<int, int>> my_swaps;
    for (int rr = 1; rr <= best_r; rr++) {
        // Jerry
        auto [x, y] = jerry[rr - 1];
        if (x != y) {
            int valx = value_at[x];
            int valy = value_at[y];
            value_at[x] = valy;
            value_at[y] = valx;
            position_of[valx] = y;
            position_of[valy] = x;
            wrongs.erase(x);
            wrongs.erase(y);
            if (value_at[x] != x) wrongs.insert(x);
            if (value_at[y] != y) wrongs.insert(y);
        }
        
        // My
        int uk = 0, vk = 0;
        if (!wrongs.empty()) {
            int i = *wrongs.begin();
            int p = position_of[i];
            if (p != i) {
                uk = i;
                vk = p;
                // Perform
                int valu = value_at[uk];
                int valv = value_at[vk];
                value_at[uk] = valv;
                value_at[vk] = valu;
                position_of[valu] = vk;
                position_of[valv] = uk;
                wrongs.erase(uk);
                wrongs.erase(vk);
                if (value_at[uk] != uk) wrongs.insert(uk);
                if (value_at[vk] != vk) wrongs.insert(vk);
            }
        }
        my_swaps.emplace_back(uk, vk);
    }
    
    cout << best_r << '\n';
    for (auto [u, v] : my_swaps) {
        cout << u << " " << v << '\n';
    }
    cout << best_v << '\n';
    
    return 0;
}