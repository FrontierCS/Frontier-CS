#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <map>

using namespace std;

map<pair<int, int>, long long> query_cache;

long long do_query(int u, int d) {
    if (query_cache.count({u, d})) {
        return query_cache[{u, d}];
    }
    cout << "? " << u << " " << d << endl;
    long long response;
    cin >> response;
    query_cache[{u, d}] = response;
    return response;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int h;
    cin >> h;
    int n = (1 << h) - 1;

    vector<long long> q_odd_cache(n + 1, -1);
    int max_dist = 2 * (h - 1);
    
    auto get_q_odd = [&](int u) {
        if (q_odd_cache[u] != -1) {
            return q_odd_cache[u];
        }
        long long current_q_odd = 0;
        for (int d = 1; d <= max_dist; d += 2) {
            current_q_odd += do_query(u, d);
        }
        q_odd_cache[u] = current_q_odd;
        return current_q_odd;
    };

    long long q_odd_1 = get_q_odd(1);

    int other_node_idx = -1;
    
    int trials = min(n, 50); 
    for (int i = 2; i <= trials; ++i) {
        if (get_q_odd(i) != q_odd_1) {
            other_node_idx = i;
            break;
        }
    }

    if (other_node_idx != -1) {
        long long total_sum = q_odd_1 + q_odd_cache[other_node_idx];
        cout << "! " << total_sum << endl;
        return 0;
    }

    if (trials < n) {
        int next_trial = trials + 1;
        if (get_q_odd(next_trial) != q_odd_1) {
            long long total_sum = q_odd_1 + q_odd_cache[next_trial];
            cout << "! " << total_sum << endl;
            return 0;
        }
    }
    
    // Fallback for the rare balanced case: S = 2 * S_odd(p_1)
    long long total_sum = 2 * q_odd_1;
    cout << "! " << total_sum << endl;

    return 0;
}