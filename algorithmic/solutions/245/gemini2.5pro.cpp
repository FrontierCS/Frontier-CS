#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>

int ask(int i, int j) {
    std::cout << "? " << i << " " << j << std::endl;
    int response;
    std::cin >> response;
    if (response == -1) {
        exit(0);
    }
    return response;
}

void answer(int i) {
    std::cout << "! " << i << std::endl;
}

void solve() {
    int n;
    std::cin >> n;

    std::vector<int> players(n);
    std::iota(players.begin(), players.end(), 1);

    while (players.size() > 2) {
        std::vector<int> next_round_players;
        for (size_t i = 0; i + 2 < players.size(); i += 3) {
            int p1 = players[i];
            int p2 = players[i + 1];
            int p3 = players[i + 2];
            int res1 = ask(p1, p2);
            if (res1 == 0) { // p1 says p2 is a knave
                int res2 = ask(p2, p1);
                if (res2 == 0) { // p2 also says p1 is a knave
                    next_round_players.push_back(p3);
                } else { // p1 and p2 disagree
                    next_round_players.push_back(p1);
                    next_round_players.push_back(p2);
                }
            } else { // p1 says p2 is a knight
                int res2 = ask(p2, p1);
                if (res2 == 1) { // p2 also says p1 is a knight
                    next_round_players.push_back(p3);
                } else { // p1 and p2 disagree
                    next_round_players.push_back(p1);
                    next_round_players.push_back(p2);
                }
            }
        }
        for (size_t i = (players.size() / 3) * 3; i < players.size(); ++i) {
            next_round_players.push_back(players[i]);
        }
        players = next_round_players;
    }

    int p1 = players[0];
    int p2 = players.size() > 1 ? players[1] : -1;
    
    int impostor_cand;

    if (p2 == -1) {
        impostor_cand = p1;
    } else {
        if (ask(p1, p2) == 1) {
            impostor_cand = p1;
        } else {
            impostor_cand = p2;
        }
    }

    std::vector<int> knight_cands;
    for (int i = 1; i <= n; ++i) {
        if (i == impostor_cand) continue;
        if (ask(i, impostor_cand) == 1) {
            knight_cands.push_back(i);
        }
    }

    int min_knights = floor(0.3 * n) + 1;
    
    if (knight_cands.size() >= min_knights -1 && ask(impostor_cand, knight_cands[0]) == 0) {
        answer(impostor_cand);
        return;
    }
    
    for (int p : knight_cands) {
         if (ask(impostor_cand, p) == 1) {
            bool all_others_agree = true;
            for (int p2 : knight_cands) {
                if (p == p2) continue;
                if (ask(p, p2) == 0) {
                    all_others_agree = false;
                    break;
                }
            }
            if(all_others_agree) {
                answer(p);
                return;
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}