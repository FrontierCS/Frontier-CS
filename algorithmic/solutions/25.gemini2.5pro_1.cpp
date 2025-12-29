#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

int n;
map<string, int> query_cache;

int do_query(const vector<int>& S) {
    if (S.empty()) {
        return 0;
    }
    string q_str(n, '0');
    for (int v : S) {
        q_str[v - 1] = '1';
    }
    
    if (query_cache.count(q_str)) {
        return query_cache[q_str];
    }

    cout << "? " << q_str << endl;
    int result;
    cin >> result;
    if (result == -1) exit(0); // Exit on error
    query_cache[q_str] = result;
    return result;
}

// f(S1, S2) > 0 iff dist(S1, S2) <= 2 in G
bool are_close(const vector<int>& S1, const vector<int>& S2) {
    if (S1.empty() || S2.empty()) return false;
    
    int q_S1 = do_query(S1);
    int q_S2 = do_query(S2);
    
    vector<int> S1_union_S2 = S1;
    S1_union_S2.insert(S1_union_S2.end(), S2.begin(), S2.end());
    int q_S1_union_S2 = do_query(S1_union_S2);

    return q_S1 + q_S2 > q_S1_union_S2;
}

void solve() {
    cin >> n;
    query_cache.clear();

    if (n == 1) {
        cout << "! 1" << endl;
        return;
    }

    vector<int> component;
    component.push_back(1);
    
    vector<bool> in_component(n + 1, false);
    in_component[1] = true;

    while(component.size() < n) {
        vector<int> unvisited;
        for (int j = 1; j <= n; ++j) {
            if (!in_component[j]) {
                unvisited.push_back(j);
            }
        }

        vector<int> candidates = unvisited;
        
        while (candidates.size() > 1) {
            int mid = candidates.size() / 2;
            vector<int> U1(candidates.begin(), candidates.begin() + mid);
            
            if (are_close(component, U1)) {
                candidates = U1;
            } else {
                candidates = vector<int>(candidates.begin() + mid, candidates.end());
            }
        }
        
        int next_v = candidates[0];
        
        vector<int> next_v_set = {next_v};
        if (!are_close(component, next_v_set)) {
            // Component can't be expanded further
            break;
        }

        component.push_back(next_v);
        in_component[next_v] = true;
    }

    if (component.size() == n) {
        cout << "! 1" << endl;
    } else {
        cout << "! 0" << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}