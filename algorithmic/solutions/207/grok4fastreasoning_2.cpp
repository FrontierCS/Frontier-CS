#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    cin >> N;
    vector<int> S(N);
    for (int i = 0; i < N; i++) {
        cin >> S[i];
    }
    vector<int> pos(N);
    for (int i = 0; i < N; i++) {
        pos[S[i]] = i;
    }
    set<int> misplaced;
    for (int i = 0; i < N; i++) {
        if (S[i] != i) {
            misplaced.insert(i);
        }
    }
    
    if (misplaced.empty()) {
        cout << 0 << '\n';
        cout << 0 << '\n';
        return 0;
    }
    
    int M;
    cin >> M;
    vector<pair<int, int>> jerry(M);
    for (int m = 0; m < M; m++) {
        int x, y;
        cin >> x >> y;
        jerry[m] = {x, y};
    }
    
    auto update_set = [&](int p) {
        bool now_mis = (S[p] != p);
        if (now_mis) {
            if (misplaced.find(p) == misplaced.end()) {
                misplaced.insert(p);
            }
        } else {
            misplaced.erase(p);
        }
    };
    
    vector<pair<int, int>> my_swaps;
    long long total_cost = 0;
    int chosen_R = 0;
    bool found = false;
    
    for (int k = 0; k < M; k++) {
        // Jerry's move
        int x = jerry[k].first;
        int y = jerry[k].second;
        if (x != y) {
            int val1 = S[x];
            int val2 = S[y];
            S[x] = val2;
            S[y] = val1;
            pos[val1] = y;
            pos[val2] = x;
            update_set(x);
            update_set(y);
        }
        
        // My move
        pair<int, int> this_swap = {0, 0};
        int cost = 0;
        if (!misplaced.empty()) {
            int i = *misplaced.begin();
            int j = pos[i];
            if (j != i) {
                this_swap = {i, j};
                cost = abs(i - j);
                // Perform swap
                int val1 = S[i];
                int val2 = S[j];
                S[i] = val2;
                S[j] = val1;
                pos[val1] = j;
                pos[val2] = i;
                update_set(i);
                update_set(j);
            }
        }
        my_swaps.emplace_back(this_swap);
        total_cost += cost;
        
        // Check if sorted
        if (misplaced.empty()) {
            chosen_R = k + 1;
            found = true;
            break;
        }
    }
    
    if (!found) {
        chosen_R = M;
        // Assume it's sorted at this point
    }
    
    long long V = (long long) chosen_R * total_cost;
    
    cout << chosen_R << '\n';
    for (int t = 0; t < chosen_R; t++) {
        auto [u, v] = my_swaps[t];
        cout << u << " " << v << '\n';
    }
    cout << V << '\n';
    
    return 0;
}