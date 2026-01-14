#include <iostream>
#include <vector>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    vector<int> parent(n + 1, 0);
    vector<int> depth(n + 1, 0);
    parent[1] = -1; // root
    depth[1] = 0;

    for (int v = 2; v <= n; ++v) {
        int best_u = -1;
        int max_depth = -1;
        for (int u = 1; u < v; ++u) {
            cout << "? 2 " << u << " 1 " << v << endl;
            int resp;
            cin >> resp;
            if (resp == -1) {
                // protocol violation, exit immediately
                return 0;
            }
            if (resp == 1) {
                if (depth[u] > max_depth) {
                    max_depth = depth[u];
                    best_u = u;
                }
            }
        }
        parent[v] = best_u;
        depth[v] = depth[best_u] + 1;
    }

    cout << "!" << endl;
    for (int v = 2; v <= n; ++v) {
        cout << v << " " << parent[v] << endl;
    }
    cout << flush;

    return 0;
}