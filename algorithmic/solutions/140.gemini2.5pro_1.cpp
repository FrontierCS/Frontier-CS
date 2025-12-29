#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <map>

using namespace std;

long long b;
int k, w;

// Function to send a query to the judge
vector<long long> query(const vector<pair<long long, long long>>& probes) {
    cout << "? " << probes.size();
    for (const auto& p : probes) {
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;
    int n_dist = k * probes.size();
    vector<long long> distances(n_dist);
    for (int i = 0; i < n_dist; ++i) {
        cin >> distances[i];
    }
    return distances;
}

// Function to submit the final answer
void answer(const vector<pair<long long, long long>>& deposits) {
    cout << "!";
    for (const auto& p : deposits) {
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;
}

// Helper to get frequency map of a vector
map<long long, int> get_freq(const vector<long long>& v) {
    map<long long, int> freq;
    for (long long x : v) {
        freq[x]++;
    }
    return freq;
}

// Backtracking function to find the correct (u,v) pairing
bool find_pairing(int u_idx, const vector<long long>& U, const vector<long long>& V,
                  vector<bool>& v_used, vector<pair<long long, long long>>& current_pairing,
                  map<long long, int>& dist_freq, long long su, long long sv) {
    if (u_idx == k) {
        return true;
    }

    long long u = U[u_idx];
    for (int i = 0; i < k; ++i) {
        if (!v_used[i]) {
            long long v = V[i];
            if ((u % 2 + 2) % 2 != (v % 2 + 2) % 2) continue;

            long long d = max(abs(u - su), abs(v - sv));
            if (dist_freq.count(d) && dist_freq[d] > 0) {
                dist_freq[d]--;
                v_used[i] = true;
                current_pairing.push_back({u, v});

                if (find_pairing(u_idx + 1, U, V, v_used, current_pairing, dist_freq, su, sv)) {
                    return true;
                }

                current_pairing.pop_back();
                v_used[i] = false;
                dist_freq[d]++;
            }
        }
    }
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> b >> k >> w;

    vector<long long> U, V;
    long long S_u = 200000000;
    long long S_v = 200000000;
    
    // Determine U coordinates
    vector<long long> u_dists = query({{(S_u/2), (S_u/2)}});
    sort(u_dists.rbegin(), u_dists.rend());
    for(long long d : u_dists) U.push_back(S_u - d);

    // Determine V coordinates
    vector<long long> v_dists = query({{(S_v/2), -(S_v/2)}});
    sort(v_dists.rbegin(), v_dists.rend());
    for(long long d : v_dists) V.push_back(S_v - d);
    
    sort(U.begin(), U.end());
    sort(V.begin(), V.end());

    // Query with a new probe to get distances for matching
    long long su = 2, sv = 0; // (s,t) = (1,1)
    vector<long long> match_dists = query({{(su+sv)/2, (su-sv)/2}});
    map<long long, int> dist_freq = get_freq(match_dists);

    vector<bool> v_used(k, false);
    vector<pair<long long, long long>> uv_pairs;

    // Find the correct pairing using backtracking
    find_pairing(0, U, V, v_used, uv_pairs, dist_freq, su, sv);
    
    vector<pair<long long, long long>> final_deposits;
    for(auto p : uv_pairs) {
        long long u = p.first;
        long long v = p.second;
        final_deposits.push_back({(u + v) / 2, (u - v) / 2});
    }

    answer(final_deposits);

    return 0;
}