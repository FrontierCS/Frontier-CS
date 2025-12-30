#include <iostream>
#include <vector>
#include <string>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n;
    while (cin >> n) {
        // Read matrix as strings and convert to integers
        vector<string> mat(n);
        for (int i = 0; i < n; ++i)
            cin >> mat[i];
        vector<vector<int>> C(n, vector<int>(n));
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < n; ++j)
                C[i][j] = mat[i][j] - '0';
        
        // Greedy construction: start with vertex 0
        vector<int> path = {0};
        vector<int> edges;   // colors of consecutive edges in current path
        int changes = 0;     // number of i with edges[i] != edges[i+1]
        bool ok = true;
        
        for (int v = 1; v < n; ++v) {
            int m = path.size();      // number of vertices currently
            int L = m - 1;            // number of edges currently
            int found = -1;
            int new_changes;
            
            // Try insertion positions from the end (to keep lexicographic order small)
            for (int pos = m; pos >= 0; --pos) {
                if (pos == m) {        // insert at the end
                    if (L == 0)
                        new_changes = 0;
                    else {
                        int last_edge = edges[L - 1];
                        int new_edge = C[path[m - 1]][v];
                        new_changes = changes + (last_edge != new_edge ? 1 : 0);
                    }
                } else if (pos == 0) { // insert at the beginning
                    if (L == 0)
                        new_changes = 0;
                    else {
                        int first_edge = edges[0];
                        int new_edge = C[v][path[0]];
                        new_changes = changes + (new_edge != first_edge ? 1 : 0);
                    }
                } else {               // insert between path[pos-1] and path[pos]
                    // Compute new edges that will replace the old edge edges[pos-1]
                    int a = C[path[pos - 1]][v];
                    int b = C[v][path[pos]];
                    
                    // Old changes that might be affected
                    int old_before = (pos - 2 >= 0 && edges[pos - 2] != edges[pos - 1]) ? 1 : 0;
                    int old_middle = (pos < L && edges[pos - 1] != edges[pos]) ? 1 : 0;
                    
                    // New changes after insertion
                    int new_before = (pos - 2 >= 0 && edges[pos - 2] != a) ? 1 : 0;
                    int new_mid1 = (a != b) ? 1 : 0;
                    int new_mid2 = (pos < L && b != edges[pos]) ? 1 : 0;
                    
                    new_changes = changes - old_before - old_middle + new_before + new_mid1 + new_mid2;
                }
                
                if (new_changes <= 1) {
                    found = pos;
                    break;
                }
            }
            
            if (found == -1) {
                ok = false;
                break;
            }
            
            // Insert vertex v at position found
            int pos = found;
            if (pos == m) {                 // at the end
                path.push_back(v);
                if (L > 0)
                    edges.push_back(C[path[m - 1]][v]);
                else
                    edges.push_back(C[path[0]][v]);
            } else if (pos == 0) {          // at the beginning
                path.insert(path.begin(), v);
                if (L > 0)
                    edges.insert(edges.begin(), C[v][path[1]]);
                else
                    edges.insert(edges.begin(), C[v][path[1]]);
            } else {                        // in the middle
                int left = path[pos - 1];
                int right = path[pos];      // vertex that will be shifted right
                int a = C[left][v];
                int b = C[v][right];
                
                path.insert(path.begin() + pos, v);
                // Update edges: replace edges[pos-1] with a and b
                edges[pos - 1] = a;
                edges.insert(edges.begin() + pos, b);
            }
            changes = new_changes;
        }
        
        if (!ok) {
            cout << -1 << '\n';
        } else {
            for (int i = 0; i < n; ++i) {
                if (i) cout << ' ';
                cout << path[i] + 1;
            }
            cout << '\n';
        }
    }
    return 0;
}