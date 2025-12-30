#include <iostream>
#include <vector>
#include <numeric>

using namespace std;

int n, m;
vector<vector<int>> poles;
vector<pair<int, int>> moves;

void move_ball(int from, int to) {
    if (from == to) return;
    if (poles[from - 1].empty()) return;
    if (poles[to - 1].size() >= m) return;

    int ball = poles[from - 1].back();
    poles[from - 1].pop_back();
    poles[to - 1].push_back(ball);
    moves.push_back({from, to});
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m;
    poles.resize(n + 1);
    for (int i = 0; i < n; ++i) {
        poles[i].resize(m);
        for (int j = 0; j < m; ++j) {
            cin >> poles[i][j];
        }
    }

    // Use pole n as a general buffer, and n+1 as secondary.
    // First, make pole n empty by moving all its balls to n+1.
    for (int i = 0; i < m; ++i) {
        move_ball(n, n + 1);
    }

    // Solve for poles 1 to n-1.
    for (int c = 1; c < n; ++c) {
        // Clear pole c. Move non-c balls to pole n, and c-balls to n+1 temporarily.
        while (true) {
            bool all_c = true;
            for (int ball : poles[c - 1]) {
                if (ball != c) {
                    all_c = false;
                    break;
                }
            }
            if (all_c) break;
            
            if (poles[c - 1].empty()) break;

            int top_ball = poles[c - 1].back();
            if (top_ball != c) {
                move_ball(c, n);
            } else {
                move_ball(c, n + 1);
            }
        }

        // Gather all c-balls from other unsorted poles.
        for (int i = c + 1; i < n; ++i) {
            while (true) {
                bool has_c = false;
                for (int ball : poles[i - 1]) {
                    if (ball == c) {
                        has_c = true;
                        break;
                    }
                }
                if (!has_c) break;
                if (poles[i-1].empty()) break;

                int top_ball = poles[i - 1].back();
                if (top_ball == c) {
                    move_ball(i, c);
                } else {
                    move_ball(i, n);
                }
            }
        }
        
        // Gather c-balls from buffer poles n and n+1.
        while (poles[c - 1].size() < m) {
            bool found_c = false;
            // Check pole n
            if (!poles[n - 1].empty()) {
                if (poles[n-1].back() == c) {
                    move_ball(n, c);
                    found_c = true;
                }
            }
            // Check pole n+1
            if (!found_c && !poles[n].empty()) {
                if(poles[n].back() == c){
                    move_ball(n+1, c);
                    found_c = true;
                }
            }
            if(!found_c) break;
        }

        // If pole c is not full, it means some c balls are buried.
        // Unstack buffers to find them.
        while(poles[c-1].size() < m){
            if(!poles[n+1-1].empty() && poles[n+1-1].back() == c){
                move_ball(n+1, c);
                continue;
            }
            if(!poles[n-1].empty() && poles[n-1].back() == c){
                move_ball(n, c);
                continue;
            }
            
            if(!poles[n-1].empty()){
                move_ball(n, n+1);
            } else if (!poles[n].empty()){
                move_ball(n+1, n);
            } else {
                 break; // Should not happen if logic is correct
            }
        }
    }

    // Finally, sort pole n. All remaining balls on n and n+1 belong to pole n.
    while (!poles[n].empty()) {
        move_ball(n + 1, n);
    }
    while (poles[n-1].size() < m) {
        move_ball(n, n);
    }

    cout << moves.size() << "\n";
    for (const auto& p : moves) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}