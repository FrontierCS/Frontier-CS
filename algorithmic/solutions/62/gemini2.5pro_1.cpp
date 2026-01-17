#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

int n, m;
std::vector<int> pillars[55];
std::vector<std::pair<int, int>> operations;

// Simulates a move and records it.
void move_ball(int from, int to) {
    if (from == to || pillars[from].empty() || pillars[to].size() >= m) {
        // Invalid move, should not happen with correct logic
        return;
    }
    int ball = pillars[from].back();
    pillars[from].pop_back();
    pillars[to].push_back(ball);
    operations.push_back({from, to});
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> m;
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < m; ++j) {
            int color;
            std::cin >> color;
            pillars[i].push_back(color);
        }
    }

    // Sort color c onto pillar c, for c = 1 to n.
    for (int c = 1; c <= n; ++c) {
        // Phase 1: Clear pillar c. Move any non-c balls to n+1.
        // Also move c-balls that are in the way to n+1.
        while (!pillars[c].empty()) {
            int ball = pillars[c].back();
            if (ball == c) {
                // This ball is correct, but might be on top of a wrong one.
                // To simplify, we move it out and bring it back later.
                // Find a safe spot on pillars > c. If none, use n+1.
                int safe_spot = -1;
                for (int j = c + 1; j <= n; ++j) {
                    if (pillars[j].size() < m) {
                        safe_spot = j;
                        break;
                    }
                }
                if (safe_spot != -1) {
                    move_ball(c, safe_spot);
                } else {
                    move_ball(c, n + 1);
                }
            } else {
                move_ball(c, n + 1);
            }
        }

        // Phase 2: Gather all balls of color c onto pillar c.
        while (pillars[c].size() < m) {
            // Find a ball of color c on pillars c+1..n or n+1.
            int src_pillar = -1;

            // Prioritize finding balls on other main pillars first
            for (int j = c + 1; j <= n; ++j) {
                for (int k = 0; k < pillars[j].size(); ++k) {
                    if (pillars[j][k] == c) {
                        src_pillar = j;
                        break;
                    }
                }
                if (src_pillar != -1) break;
            }

            // If not found, search on the auxiliary pillar
            if (src_pillar == -1) {
                for (int k = 0; k < pillars[n + 1].size(); ++k) {
                    if (pillars[n + 1][k] == c) {
                        src_pillar = n + 1;
                        break;
                    }
                }
            }
            
            // This should always find a pillar, as we haven't collected all m balls yet.
            if (src_pillar == -1) break;

            // Move balls from src_pillar until the c-ball is at the top.
            while (pillars[src_pillar].back() != c) {
                // Buffer management: if n+1 is full, move its top to an unsorted pillar.
                if (pillars[n + 1].size() == m) {
                    int target_pillar = -1;
                    for (int j = c + 1; j <= n; ++j) {
                        if (pillars[j].size() < m) {
                            target_pillar = j;
                            break;
                        }
                    }
                    move_ball(n + 1, target_pillar);
                }
                move_ball(src_pillar, n + 1);
            }

            // Move the c-ball to pillar c.
            move_ball(src_pillar, c);
        }
    }

    std::cout << operations.size() << "\n";
    for (const auto& op : operations) {
        std::cout << op.first << " " << op.second << "\n";
    }

    return 0;
}