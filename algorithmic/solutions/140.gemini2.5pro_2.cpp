#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <set>
#include <map>

using namespace std;

long long b;
int k;
int w;

// Function to send a query and receive distances
vector<long long> query(int d, const vector<pair<long long, long long>>& probes) {
    cout << "? " << d;
    for (const auto& p : probes) {
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;

    vector<long long> distances(k * d);
    for (int i = 0; i < k * d; ++i) {
        cin >> distances[i];
    }
    return distances;
}

// Function to find pairings for one parity group
void solve_parity(multiset<long long>& u_set, multiset<long long>& v_set, vector<pair<long long, long long>>& solutions) {
    while (!u_set.empty()) {
        long long u = *u_set.begin();
        u_set.erase(u_set.begin());

        // Create a vector of unique v values to test
        vector<long long> distinct_v;
        if (!v_set.empty()) {
            distinct_v.push_back(*v_set.begin());
            for (long long val : v_set) {
                if (val != distinct_v.back()) {
                    distinct_v.push_back(val);
                }
            }
        }
        
        for (long long v : distinct_v) {
            long long two_x = u + v;
            long long two_y = u - v;

            // From x,y in [-b,b], we have |x+y|<=2b, |x-y|<=2b
            if (abs(two_x) > 2LL * b || abs(two_y) > 2LL * b) {
                continue;
            }

            long long x = two_x / 2;
            long long y = two_y / 2;
            
            // Check if coordinates are within the original boundary b
            if (abs(x) > b || abs(y) > b) {
                continue;
            }
            
            // Probe coordinates must be within [-10^8, 10^8]
            if (abs(x) > 100000000 || abs(y) > 100000000) {
                 continue;
            }

            vector<long long> dists = query(1, {{x, y}});
            
            if (dists[0] == 0) {
                solutions.push_back({x, y});
                v_set.erase(v_set.find(v));
                break;
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> b >> k >> w;

    long long S = 100000000;

    // First query to find multiset {x_i + y_i}
    vector<long long> u_dists = query(1, {{S, S}});
    multiset<long long> u_all;
    for (long long d : u_dists) {
        u_all.insert(2 * S - d);
    }

    // Second query to find multiset {x_i - y_i}
    vector<long long> v_dists = query(1, {{S, -S}});
    multiset<long long> v_all;
    for (long long d : v_dists) {
        v_all.insert(2 * S - d);
    }

    // Partition u and v sets by parity
    multiset<long long> u_even, u_odd, v_even, v_odd;
    for (long long u : u_all) {
        if ((u % 2 + 2) % 2 == 0) u_even.insert(u);
        else u_odd.insert(u);
    }
    for (long long v : v_all) {
        if ((v % 2 + 2) % 2 == 0) v_even.insert(v);
        else v_odd.insert(v);
    }

    vector<pair<long long, long long>> solutions;
    solve_parity(u_even, v_even, solutions);
    solve_parity(u_odd, v_odd, solutions);

    // Output final answer
    cout << "!";
    for (const auto& p : solutions) {
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;

    return 0;
}