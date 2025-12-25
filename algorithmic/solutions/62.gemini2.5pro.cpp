#include <iostream>
#include <vector>
#include <deque>
#include <utility>
#include <string>
#include <algorithm>

int n, m;
std::vector<std::deque<int>> pillars;
std::vector<std::pair<int, int>> operations;

// Function to perform a move and record it.
void move_ball(int from, int to) {
    if (from == to) return;
    int ball = pillars[from].back();
    pillars[from].pop_back();
    pillars[to].push_back(ball);
    operations.push_back({from, to});
}

// Finds the position of a ball of target_color.
// Searches in pillars >= start_pillar_idx and pillar n+1.
// Returns {pillar_idx, ball_idx_from_bottom}. Returns {-1, -1} if not found.
std::pair<int, int> find_ball(int target_color, int start_pillar_idx) {
    // Search in pillars start_pillar_idx to n
    for (int j = start_pillar_idx; j <= n; ++j) {
        for (int k = 0; k < pillars[j].size(); ++k) {
            if (pillars[j][k] == target_color) {
                return {j, k};
            }
        }
    }
    // Search in pillar n+1
    for (int k = 0; k < pillars[n + 1].size(); ++k) {
        if (pillars[n + 1][k] == target_color) {
            return {n + 1, k};
        }
    }
    return {-1, -1};
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> m;
    pillars.resize(n + 2);
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < m; ++j) {
            int color;
            std::cin >> color;
            pillars[i].push_back(color);
        }
    }

    for (int c = 1; c <= n; ++c) {
        // Goal: Fill pillar c with m balls of color c.
        // Pillars 1 to c-1 are already sorted and full. Do not touch.

        // Phase 1: Clear pillar c of incorrect balls.
        // An incorrect ball is any ball with color != c, or a ball of color c
        // that is sitting on top of an incorrect ball.
        while (true) {
            bool moved = false;
            for (int i = 0; i < pillars[c].size(); ++i) {
                if (pillars[c][i] != c) {
                    // This ball is incorrect. Move it and everything above it to pillar n+1.
                    int num_to_move = pillars[c].size() - i;
                    for (int k = 0; k < num_to_move; ++k) {
                        move_ball(c, n + 1);
                    }
                    moved = true;
                    break;
                }
            }
            if (!moved) break;
        }

        // Phase 2: Fill pillar c with balls of color c until it's full.
        while (pillars[c].size() < m) {
            // Find a ball of color c on any other unsorted pillar.
            // Pillars 1..c-1 are sorted, c is the target.
            // So we search c+1..n and n+1.
            auto pos = find_ball(c, c + 1);
            int src_p = pos.first;
            int src_idx = pos.second;

            // Excavate the ball by moving balls on top to pillar n+1.
            int balls_on_top_count = pillars[src_p].size() - 1 - src_idx;
            for (int i = 0; i < balls_on_top_count; ++i) {
                move_ball(src_p, n + 1);
            }
            
            // Move the target ball to pillar c.
            move_ball(src_p, c);
        }
    }

    std::cout << operations.size() << "\n";
    for (const auto& op : operations) {
        std::cout << op.first << " " << op.second << "\n";
    }

    return 0;
}