#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int n, m;
vector<vector<int>> poles;
vector<pair<int, int>> moves;

void do_move(int x, int y) {
    if (x == y || poles[x-1].empty() || poles[y-1].size() >= m) {
        return;
    }
    moves.push_back({x, y});
    int ball = poles[x-1].back();
    poles[x-1].pop_back();
    poles[y-1].push_back(ball);
}

// Find a pole with available space for dumping a ball from source_pole
// in stage i. We try to avoid polluting the target pole i.
int find_dump_pole(int current_stage_pole, int source_pole) {
    // Try to find a pole other than the source and target pole first
    for (int p = current_stage_pole + 1; p <= n; ++p) {
        if (p != source_pole && poles[p-1].size() < m) {
            return p;
        }
    }
    // n+1 pole is a good general purpose dump
    if (n + 1 != source_pole && poles[n].size() < m) {
        return n + 1;
    }
    
    // If no other choice, use the target pole if it's not the source
    if (current_stage_pole != source_pole && poles[current_stage_pole-1].size() < m) {
        return current_stage_pole;
    }
    
    // Fallback, any pole that is not the source pole
    for (int p = current_stage_pole; p <= n + 1; ++p) {
        if (p != source_pole && poles[p-1].size() < m) {
            return p;
        }
    }
    
    return -1; // Should not happen
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

    // Solve for each pole i from 1 to n, making it the home for color i
    for (int i = 1; i <= n; ++i) {
        // Stage i: make pole i contain m balls of color i

        // 1. Clean pole i: move balls that are not color i and are above the contiguous block of i's at the bottom
        int good_balls_at_bottom = 0;
        for (int ball_color : poles[i-1]) {
            if (ball_color == i) {
                good_balls_at_bottom++;
            } else {
                break;
            }
        }
        
        while (poles[i-1].size() > good_balls_at_bottom) {
            int dest = find_dump_pole(i, i);
            do_move(i, dest);
        }

        // 2. Fill pole i with balls of color i
        while (poles[i-1].size() < m) {
            // Find the highest ball of color i in other poles
            int best_pole = -1;
            int best_pos = -1;

            for (int p = i + 1; p <= n + 1; ++p) {
                for (int k = 0; k < poles[p-1].size(); ++k) {
                    if (poles[p-1][k] == i) {
                        if (k > best_pos) {
                            best_pos = k;
                            best_pole = p;
                        }
                    }
                }
            }

            if (best_pole == -1) {
                // All remaining balls of color i are already on pole i.
                break;
            }

            // Dig out the ball from best_pole
            while ((int)poles[best_pole-1].size() - 1 > best_pos) {
                int dest = find_dump_pole(i, best_pole);
                do_move(best_pole, dest);
            }

            // Move the ball of color i to pole i
            do_move(best_pole, i);
        }

        // 3. Final cleanup of pole i, in case it was used as a dump pole
        while (!poles[i-1].empty() && poles[i-1].back() != i) {
            int dest = find_dump_pole(i, i);
            do_move(i, dest);
        }
    }

    cout << moves.size() << "\n";
    for (const auto& move : moves) {
        cout << move.first << " " << move.second << "\n";
    }

    return 0;
}