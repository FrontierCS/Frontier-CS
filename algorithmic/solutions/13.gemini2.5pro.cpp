#include <iostream>
#include <vector>
#include <set>
#include <algorithm>
#include <utility>

void solve() {
    int sx, sy;
    std::cin >> sx >> sy;

    std::set<std::pair<int, int>> black_cells;
    int rx = sx, ry = sy;

    while (true) {
        // We herd the robot towards (1, 1) by blocking moves (dx, dy) where dx+dy >= 0.
        // These are (1,1), (1,0), (0,1), (1,-1), (-1,1).
        
        std::vector<std::pair<int, int>> targets;
        int cand_dx[] = {1, 1, 0, 1, -1};
        int cand_dy[] = {1, 0, 1, -1, 1};

        for (int i = 0; i < 5; ++i) {
            int nx = rx + cand_dx[i];
            int ny = ry + cand_dy[i];
            if (nx > 0 && ny > 0 && nx <= 3000 && ny <= 3000) {
                targets.push_back({nx, ny});
            }
        }

        std::pair<int, int> to_color = {-1, -1};
        for (const auto& p : targets) {
            if (black_cells.find(p) == black_cells.end()) {
                to_color = p;
                break;
            }
        }

        if (to_color.first == -1) {
            // This case means all "forward" cells are already colored.
            // The robot is forced to retreat (nx+ny < rx+ry).
            // We use this turn to further trap the robot by coloring one of its 
            // remaining valid move destinations. This will eventually surround it.
            bool colored = false;
            for (int dx = -1; dx <= 1; ++dx) {
                for (int dy = -1; dy <= 1; ++dy) {
                    if (dx == 0 && dy == 0) continue;
                    int nx = rx + dx;
                    int ny = ry + dy;
                    if (nx > 0 && ny > 0 && nx <= 3000 && ny <= 3000) {
                        if (black_cells.find({nx, ny}) == black_cells.end()) {
                            to_color = {nx, ny};
                            colored = true;
                            break;
                        }
                    }
                }
                if (colored) break;
            }
            // If all 8 neighbors are already black, the robot is trapped.
            // We still make a valid move; the robot will explode on its turn.
            if (!colored) {
                 to_color = {1, 1}; // A default valid cell if somehow needed
                 if(black_cells.count(to_color)) to_color = {3000, 3000};
            }
        }
        
        std::cout << to_color.first << " " << to_color.second << std::endl;
        black_cells.insert(to_color);

        std::cin >> rx >> ry;
        if (rx == 0 && ry == 0) {
            break;
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}