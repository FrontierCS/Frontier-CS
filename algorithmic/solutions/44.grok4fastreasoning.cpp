#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    cin >> N;
    
    vector<pair<long long, long long>> coords(N);
    for (int i = 0; i < N; i++) {
        cin >> coords[i].first >> coords[i].second;
    }
    
    if (N == 1) { // Though N >=2, but safe
        cout << 2 << '\n' << 0 << '\n' << 0 << '\n';
        return 0;
    }
    
    vector<char> is_prime(N, 1);
    is_prime[0] = 0;
    is_prime[1] = 0;
    for (long long i = 2; i < N; i++) {
        if (is_prime[i]) {
            for (long long jj = i * i; jj < N; jj += i) {
                if (jj >= N) break;
                is_prime[jj] = 0;
            }
        }
    }
    
    vector<int> free_p;
    for (int j = 1; j < N; j++) {
        if ((j % 10 != 9) && is_prime[j]) {
            free_p.push_back(j);
        }
    }
    
    vector<int> tour(N + 1);
    tour[0] = 0;
    for (int i = 1; i < N; i++) {
        tour[i] = i;
    }
    tour[N] = 0;
    
    set<int> available(free_p.begin(), free_p.end());
    
    vector<int> crit;
    for (int j = 9; j < N; j += 10) {
        crit.push_back(j);
    }
    
    // Handle special last position if critical and not prime
    int last_pos = N - 1;
    if (last_pos >= 1 && (last_pos % 10 == 9) && !is_prime[tour[last_pos]]) {
        if (!available.empty()) {
            auto it = available.lower_bound(last_pos);
            int d1 = INT_MAX, c1 = -1;
            if (it != available.end()) {
                c1 = *it;
                d1 = abs(c1 - last_pos);
            }
            int d2 = INT_MAX, c2 = -1;
            if (it != available.begin()) {
                auto pit = it;
                --pit;
                c2 = *pit;
                d2 = abs(c2 - last_pos);
            }
            int chosen = -1;
            if (d1 <= d2 && c1 != -1) {
                chosen = c1;
            } else if (c2 != -1) {
                chosen = c2;
            }
            if (chosen != -1) {
                swap(tour[last_pos], tour[chosen]);
                available.erase(chosen);
            }
        }
    }
    
    // Now handle other critical positions left to right
    for (int pos : crit) {
        if (is_prime[tour[pos]]) continue;
        if (available.empty()) continue;
        
        auto it = available.lower_bound(pos);
        int d1 = INT_MAX, c1 = -1;
        if (it != available.end()) {
            c1 = *it;
            d1 = abs(c1 - pos);
        }
        int d2 = INT_MAX, c2 = -1;
        if (it != available.begin()) {
            auto pit = it;
            --pit;
            c2 = *pit;
            d2 = abs(c2 - pos);
        }
        int chosen = -1;
        if (d1 < d2 && c1 != -1) {
            chosen = c1;
        } else if (d2 <= d1 && c2 != -1) {
            chosen = c2;
        } else if (c1 != -1) {
            chosen = c1;
        }
        if (chosen != -1) {
            swap(tour[pos], tour[chosen]);
            available.erase(chosen);
        }
    }
    
    cout << N + 1 << '\n';
    for (int i = 0; i <= N; i++) {
        cout << tour[i] << '\n';
    }
    
    return 0;
}