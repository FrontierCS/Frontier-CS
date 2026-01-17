#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
using namespace std;

typedef long long ll;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int N;
    cin >> N;
    vector<int> S(N);
    for (int i = 0; i < N; ++i) {
        cin >> S[i];
    }
    
    // position of each element
    vector<int> pos(N);
    for (int i = 0; i < N; ++i) {
        pos[S[i]] = i;
    }
    
    // total distance to correct positions
    ll D = 0;
    for (int e = 0; e < N; ++e) {
        D += abs(pos[e] - e);
    }
    
    int M;
    cin >> M;
    vector<int> X(M), Y(M);
    for (int j = 0; j < M; ++j) {
        cin >> X[j] >> Y[j];
    }
    
    vector<pair<int, int>> our;
    int R = M;
    
    for (int k = 0; k < M; ++k) {
        int uj = X[k], vj = Y[k];
        
        // Jerry's swap
        if (uj != vj) {
            int a = S[uj], b = S[vj];
            ll delta_j = (abs(vj - a) - abs(uj - a)) + (abs(uj - b) - abs(vj - b));
            swap(S[uj], S[vj]);
            pos[a] = vj;
            pos[b] = uj;
            D += delta_j;
        }
        
        // Candidates for our swap
        vector<pair<int, int>> cand;
        cand.emplace_back(0, 0);                  // dummy
        cand.emplace_back(uj, vj);                // cancel Jerry
        int a = S[uj];
        int b = S[vj];
        if (a != uj) cand.emplace_back(uj, a);   // put a at its correct position
        if (b != vj) cand.emplace_back(vj, b);   // put b at its correct position
        int pos_x = pos[uj];                      // where element uj currently is
        if (pos_x != uj) cand.emplace_back(uj, pos_x);
        int pos_y = pos[vj];                      // where element vj currently is
        if (pos_y != vj) cand.emplace_back(vj, pos_y);
        
        // Evaluate each candidate
        int best_u = 0, best_v = 0;
        ll best_delta = 0, best_cost = 0;
        bool first = true;
        
        for (auto &p : cand) {
            int u = p.first, v = p.second;
            ll delta, cost = abs(u - v);
            if (u == v) {
                delta = 0;
            } else {
                int au = S[u], av = S[v];
                delta = (abs(v - au) - abs(u - au)) + (abs(u - av) - abs(v - av));
            }
            
            if (first) {
                best_u = u; best_v = v;
                best_delta = delta;
                best_cost = cost;
                first = false;
            } else if (delta < best_delta || (delta == best_delta && cost < best_cost)) {
                best_u = u; best_v = v;
                best_delta = delta;
                best_cost = cost;
            }
        }
        
        // Apply our swap
        if (best_u != best_v) {
            int au = S[best_u], av = S[best_v];
            swap(S[best_u], S[best_v]);
            pos[au] = best_v;
            pos[av] = best_u;
            D += best_delta;
        }
        our.emplace_back(best_u, best_v);
        
        // If sorted, stop early
        if (D == 0) {
            R = k + 1;
            break;
        }
    }
    
    // Compute total cost and V
    ll total_cost = 0;
    for (int i = 0; i < R; ++i) {
        total_cost += abs(our[i].first - our[i].second);
    }
    ll V = R * total_cost;
    
    // Output
    cout << R << "\n";
    for (int i = 0; i < R; ++i) {
        cout << our[i].first << " " << our[i].second << "\n";
    }
    cout << V << "\n";
    
    return 0;
}