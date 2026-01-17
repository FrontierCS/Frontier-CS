#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int n, m;
vector<int> pillars[55];
vector<pair<int, int>> moves;

void do_move(int from, int to) {
    if (from == to || pillars[from].empty() || pillars[to].size() >= m) {
        return;
    }
    int ball = pillars[from].back();
    pillars[from].pop_back();
    pillars[to].push_back(ball);
    moves.push_back({from, to});
}

bool is_pillar_sorted(int p_idx) {
    if (pillars[p_idx].size() != m) {
        return false;
    }
    for (int ball : pillars[p_idx]) {
        if (ball != p_idx) {
            return false;
        }
    }
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m;
    for (int i = 1; i <= n; ++i) {
        pillars[i].reserve(n * m);
        for (int j = 0; j < m; ++j) {
            int color;
            cin >> color;
            pillars[i].push_back(color);
        }
    }
    pillars[n + 1].reserve(n * m);

    // Goal: move all balls of color c to pillar c
    for (int c = 1; c <= n; ++c) {
        if (is_pillar_sorted(c)) {
            continue;
        }

        // Phase 1: Move balls that are not color c from pillar c to pillar n+1
        while (true) {
            bool all_c = true;
            for (int ball : pillars[c]) {
                if (ball != c) {
                    all_c = false;
                    break;
                }
            }
            if (all_c) break;
            
            if (pillars[c].back() != c) {
                do_move(c, n + 1);
            } else {
                // Top is c, but something below is not. We need to find a non-full pillar to move it.
                int free_pillar = -1;
                for (int i = 1; i <= n; ++i) {
                    if (i != c && pillars[i].size() < m) {
                        free_pillar = i;
                        break;
                    }
                }
                if (free_pillar != -1) {
                    do_move(c, free_pillar);
                } else {
                    // This case is tricky, means all other pillars are full.
                    // Just move to n+1, it must have space if we are careful.
                    do_move(c, n+1);
                }
            }
        }

        // Phase 2: Gather all balls of color c onto pillar c
        while (pillars[c].size() < m) {
            // Find a ball of color c, preferably on top of a pillar
            int best_pillar = -1;
            for (int i = 1; i <= n; ++i) {
                if (i == c) continue;
                if (!pillars[i].empty() && pillars[i].back() == c) {
                    best_pillar = i;
                    break;
                }
            }

            if (best_pillar != -1) {
                do_move(best_pillar, c);
            } else {
                // No ball of color c is on top. Find one and expose it.
                int pillar_to_dig = -1;
                for (int i = 1; i <= n; ++i) {
                    if (i == c) continue;
                    for (size_t j = 0; j < pillars[i].size(); ++j) {
                        if (pillars[i][j] == c) {
                            pillar_to_dig = i;
                            break;
                        }
                    }
                    if (pillar_to_dig != -1) break;
                }
                
                // If no c balls left anywhere, check buffer
                if (pillar_to_dig == -1) {
                   while (pillars[c].size() < m && !pillars[n+1].empty()) {
                        if (pillars[n+1].back() == c) {
                            do_move(n+1, c);
                        } else {
                            // find somewhere else to put it
                            int free_pillar = -1;
                             for (int i = 1; i <= n; ++i) {
                                if (i != c && pillars[i].size() < m) {
                                    free_pillar = i;
                                    break;
                                }
                            }
                            if (free_pillar != -1) do_move(n+1, free_pillar);
                            else break; // Should not happen
                        }
                   }
                   break;
                }

                while (pillars[pillar_to_dig].back() != c) {
                    do_move(pillar_to_dig, n + 1);
                }
                do_move(pillar_to_dig, c);
            }
        }

        // Phase 3: clear buffer
        while(!pillars[n+1].empty()){
            int ball_color = pillars[n+1].back();
            if (ball_color == c && pillars[c].size() < m) {
                do_move(n+1, c);
            } else {
                int free_pillar = -1;
                for (int i = 1; i <= n; ++i) {
                    if (i != c && pillars[i].size() < m) {
                        free_pillar = i;
                        break;
                    }
                }
                if(free_pillar != -1) {
                    do_move(n+1, free_pillar);
                } else {
                    // All pillars are full. This means some pillar must be wrong.
                    // Find a pillar that is not sorted and move top to buffer
                    int wrong_pillar = -1;
                    for (int i = 1; i <= n; ++i) {
                        if (i != c && !is_pillar_sorted(i)) {
                            wrong_pillar = i;
                            break;
                        }
                    }
                    if (wrong_pillar != -1) {
                        do_move(wrong_pillar, n+1);
                    } else {
                        // This indicates a logic deadlock or completion
                        break;
                    }
                }
            }
        }
    }

    cout << moves.size() << "\n";
    for (const auto& p : moves) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}