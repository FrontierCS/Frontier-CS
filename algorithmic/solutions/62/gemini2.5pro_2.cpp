#include <iostream>
#include <vector>
#include <numeric>

int n, m;
std::vector<std::vector<int>> pillars;
std::vector<std::pair<int, int>> moves;

void do_move(int from, int to) {
    if (from == to) return;
    int ball = pillars[from].back();
    pillars[from].pop_back();
    pillars[to].push_back(ball);
    moves.push_back({from, to});
}

void swap_balls(int p1, int h1, int p2, int h2) {
    int empty_pillar = n + 1;

    int s1 = pillars[p1].size();
    int s2 = pillars[p2].size();

    int d1_above = s1 - 1 - h1;
    int d2_above = s2 - 1 - h2;
    
    if (p1 == p2) {
        // Same pillar swap: p1[h1] <-> p1[h2], assume h1 < h2
        if (h1 > h2) {
            std::swap(h1, h2);
            d1_above = s1 - 1 - h1;
            d2_above = s1 - 1 - h2;
        }

        int d_mid = h2 - h1 - 1;

        for (int k = 0; k < d2_above; ++k) do_move(p1, empty_pillar);
        do_move(p1, empty_pillar); // ball from h2
        for (int k = 0; k < d_mid; ++k) do_move(p1, empty_pillar);
        do_move(p1, empty_pillar); // ball from h1
        
        do_move(empty_pillar, p1); // ball from h2
        for (int k = 0; k < d_mid; ++k) do_move(empty_pillar, p1);
        do_move(empty_pillar, p1); // ball from h1
        for (int k = 0; k < d2_above; ++k) do_move(empty_pillar, p1);
    } else {
        // Different pillar swap
        for (int k = 0; k < d1_above; ++k) do_move(p1, empty_pillar);
        do_move(p1, empty_pillar); // Ball from p1[h1]

        for (int k = 0; k < d2_above; ++k) do_move(p2, p1);
        do_move(p2, p1); // Ball from p2[h2]

        for (int k = 0; k < d2_above; ++k) do_move(p1, p2);
        do_move(empty_pillar, p2); // Ball from p1[h1] to p2

        for (int k = 0; k < d1_above; ++k) do_move(empty_pillar, p1);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> m;
    pillars.resize(n + 2);
    for (int i = 1; i <= n; ++i) {
        pillars[i].resize(m);
        for (int j = 0; j < m; ++j) {
            std::cin >> pillars[i][j];
        }
    }

    for (int i = 1; i <= n; ++i) {
        for (int h = 0; h < m; ++h) {
            if (pillars[i][h] != i) {
                int found_p = -1, found_h = -1;

                // Find the highest ball of color i on pillar i > h
                for (int h2 = pillars[i].size() - 1; h2 > h; --h2) {
                    if (pillars[i][h2] == i) {
                        found_p = i;
                        found_h = h2;
                        break;
                    }
                }

                // If not found, find the highest ball on other pillars
                if (found_p == -1) {
                    for (int j = i + 1; j <= n; ++j) {
                        for (int h2 = pillars[j].size() - 1; h2 >= 0; --h2) {
                            if (pillars[j][h2] == i) {
                                found_p = j;
                                found_h = h2;
                                goto found_partner;
                            }
                        }
                    }
                }
                
                found_partner:;
                swap_balls(i, h, found_p, found_h);
            }
        }
    }

    std::cout << moves.size() << "\n";
    for (const auto& move : moves) {
        std::cout << move.first << " " << move.second << "\n";
    }

    return 0;
}