#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int t;
    cin >> t;
    while (t--) {
        int n, m, start, base_move_count;
        cin >> n >> m >> start >> base_move_count;
        // Read and ignore the edges
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
        }
        // Ignore the newline after the last edge
        cin.ignore();
        
        string line;
        while (true) {
            if (!getline(cin, line)) break;
            if (line.empty()) continue;
            // Check for end of map
            if (line[0] == 'A' || line[0] == 'F') {
                // AC or F
                break;
            }
            
            stringstream ss(line);
            int d;
            ss >> d;
            int chosen = 1;
            for (int i = 1; i <= d; ++i) {
                int deg, flag;
                ss >> deg >> flag;
                if (flag == 0) {
                    chosen = i;
                    break;
                }
            }
            cout << chosen << endl;
            cout.flush();
        }
    }
    return 0;
}