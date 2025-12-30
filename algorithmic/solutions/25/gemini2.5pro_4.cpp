#include <iostream>
#include <vector>
#include <string>
#include <numeric>

using namespace std;

int n;

int do_query(const vector<bool>& s_mask) {
    cout << "? ";
    string query_str(n, '0');
    for (int i = 1; i <= n; ++i) {
        if (s_mask[i]) {
            query_str[i - 1] = '1';
        }
    }
    cout << query_str << endl;
    int response;
    cin >> response;
    return response;
}

void solve() {
    cin >> n;

    if (n == 1) {
        cout << "! 1" << endl;
        return;
    }

    vector<bool> component(n + 1, false);
    component[1] = true;
    int component_size = 1;

    while (component_size < n) {
        vector<int> unvisited;
        for (int i = 1; i <= n; ++i) {
            if (!component[i]) {
                unvisited.push_back(i);
            }
        }

        int qC = do_query(component);
        if (qC == 0) {
            cout << "! 0" << endl;
            return;
        }

        int low = 0, high = unvisited.size() - 1;
        int neighbor_idx = high;

        while (low <= high) {
            int mid = low + (high - low) / 2;
            
            vector<bool> S_mask(n + 1, false);
            for (int i = 0; i <= mid; ++i) {
                S_mask[unvisited[i]] = true;
            }

            int qS = do_query(S_mask);

            vector<bool> C_union_S_mask = component;
            for (int i = 0; i <= mid; ++i) {
                C_union_S_mask[unvisited[i]] = true;
            }
            int qCS = do_query(C_union_S_mask);

            if (qC + qS > qCS) {
                neighbor_idx = mid;
                high = mid - 1;
            } else {
                low = mid + 1;
            }
        }
        
        component[unvisited[neighbor_idx]] = true;
        component_size++;
    }

    cout << "! 1" << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}