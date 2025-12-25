#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using namespace std;

int main() {
    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        int n, m, start, base_move_count;
        cin >> n >> m >> start >> base_move_count;
        // read and ignore edges
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
        }
        // ignore newline after edges
        cin.ignore();

        bool done = false;
        while (!done) {
            string line;
            getline(cin, line);
            if (line.empty()) continue;
            if (line[0] == 'A' || line[0] == 'F') {
                // AC or F
                done = true;
                continue;
            }
            stringstream ss(line);
            int d;
            ss >> d;
            vector<int> deg(d), flag(d);
            for (int i = 0; i < d; ++i) {
                ss >> deg[i] >> flag[i];
            }
            // choose first unvisited neighbor, else first neighbor
            int move = 1;
            for (int i = 0; i < d; ++i) {
                if (flag[i] == 0) {
                    move = i + 1;
                    break;
                }
            }
            cout << move << endl;
            cout.flush();
        }
    }
    return 0;
}