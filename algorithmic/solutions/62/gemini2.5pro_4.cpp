#include <iostream>
#include <vector>
#include <utility>
#include <numeric>

int n, m;
std::vector<int> pillars[55];
std::vector<std::pair<int, int>> moves;

void move_ball(int from, int to) {
    if (from == to || pillars[from].empty()) {
        return;
    }
    int ball = pillars[from].back();
    pillars[from].pop_back();
    pillars[to].push_back(ball);
    moves.push_back({from, to});
}

void move_all(int from, int to) {
    while (!pillars[from].empty()) {
        move_ball(from, to);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> m;
    for (int i = 1; i <= n; ++i) {
        pillars[i].resize(m);
        for (int j = 0; j < m; ++j) {
            std::cin >> pillars[i][j];
        }
    }

    // Strategy: Sort colors one by one. For color i, move all balls of color i to pillar i.
    // Pillars 1 to i-1 are already sorted.
    for (int i = 1; i <= n; ++i) {
        // First, move all balls from unsorted pillars (i to n) to the buffer pillar (n+1).
        for (int j = i; j <= n; ++j) {
            move_all(j, n + 1);
        }

        // Now, redistribute balls from n+1.
        // Balls of color i go to pillar i.
        // Balls of other colors k > i go to pillar k (as temporary storage for the next steps).
        while (!pillars[n + 1].empty()) {
            int ball_color = pillars[n + 1].back();
            if (ball_color == i) {
                move_ball(n + 1, i);
            } else {
                move_ball(n + 1, ball_color);
            }
        }
        
        // At this point, pillar i is sorted and full.
        // The remaining balls are on their respective destination pillars, ready for the next iteration.
    }

    std::cout << moves.size() << "\n";
    for (const auto& move : moves) {
        std::cout << move.first << " " << move.second << "\n";
    }

    return 0;
}