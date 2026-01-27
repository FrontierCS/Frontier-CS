#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) {
        // If no input, output a valid minimal answer
        cout << 1 << " " << 1 << "\n";
        return 0;
    }
    vector<int> a(n + 1);
    for (int i = 1; i <= n; i++) {
        if (!(cin >> a[i])) {
            // Fallback to self-loop if input incomplete
            a[i] = i;
        }
    }
    
    vector<int> state(n + 1, 0); // 0=unvisited, 1=visiting, 2=done
    vector<int> cycleId(n + 1, 0);
    int cycleCnt = 0;
    
    for (int i = 1; i <= n; i++) {
        if (state[i] != 0) continue;
        vector<int> st;
        int u = i;
        while (true) {
            if (state[u] == 0) {
                st.push_back(u);
                state[u] = 1;
                u = a[u];
            } else if (state[u] == 1) {
                // Found a new cycle
                ++cycleCnt;
                // Mark cycle nodes
                while (!st.empty()) {
                    int v = st.back(); st.pop_back();
                    cycleId[v] = cycleCnt;
                    state[v] = 2;
                    if (v == u) break;
                }
                // Remaining are pre-cycle nodes leading to this cycle
                while (!st.empty()) {
                    int v = st.back(); st.pop_back();
                    cycleId[v] = cycleCnt;
                    state[v] = 2;
                }
                break;
            } else { // state[u] == 2
                int id = cycleId[u];
                while (!st.empty()) {
                    int v = st.back(); st.pop_back();
                    cycleId[v] = id;
                    state[v] = 2;
                }
                break;
            }
        }
    }
    
    int targetId = cycleId[1];
    vector<int> ans;
    for (int i = 1; i <= n; i++) {
        if (cycleId[i] == targetId) ans.push_back(i);
    }
    
    cout << ans.size();
    for (int x : ans) cout << " " << x;
    cout << "\n";
    return 0;
}