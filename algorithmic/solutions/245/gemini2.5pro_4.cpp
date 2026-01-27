#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>

int query(int i, int j) {
    std::cout << "? " << i << " " << j << std::endl;
    int result;
    std::cin >> result;
    if (result == -1) exit(0);
    return result;
}

void solve() {
    int n;
    std::cin >> n;

    std::vector<int> players(n);
    std::iota(players.begin(), players.end(), 1);

    while (players.size() > 2) {
        std::vector<int> next_round;
        for (size_t i = 0; i + 2 < players.size(); i += 3) {
            int p1 = players[i];
            int p2 = players[i+1];
            int p3 = players[i+2];
            int r12 = query(p1, p2);
            if (r12 == 1) { 
                int r23 = query(p2, p3);
                if (r23 == 1) { 
                    next_round.push_back(p1);
                } else {
                    next_round.push_back(p1);
                }
            } else {
                int r13 = query(p1, p3);
                if (r13 == 1) {
                    next_round.push_back(p1);
                } else {
                    next_round.push_back(p2);
                }
            }
        }
        size_t grouped_count = (players.size() / 3) * 3;
        for (size_t i = grouped_count; i < players.size(); ++i) {
            next_round.push_back(players[i]);
        }
        players = next_round;
    }

    int p_cand = players[0];
    if (players.size() == 2) {
       if (query(players[0], players[1]) == 0) {
           p_cand = players[1];
       }
    }

    std::vector<int> group1;
    std::vector<int> group2;
    
    for (int i = 1; i <= n; i++) {
        if (i == p_cand) continue;
        if (query(p_cand, i) == 1) {
            group1.push_back(i);
        } else {
            group2.push_back(i);
        }
    }
    group1.push_back(p_cand);
    
    std::vector<int> KNI, KNV;
    int min_knights = floor(0.3 * n) + 1;

    if (group1.size() >= min_knights) {
        KNI = group1;
        KNV = group2;
    } else {
        KNI = group2;
        KNV = group1;
    }
    
    int knight_ref = -1;
    if (KNI.size() >= 2) {
        int u = KNI[0], v = KNI[1];
        if (query(u, v) == 1) {
            knight_ref = u;
        } else {
            knight_ref = v;
        }
    } else if (KNI.size() == 1) {
        knight_ref = KNI[0];
    } else {
       // This case should be impossible under problem constraints.
       // The problem guarantees K > 0.3n >= 1.
       // KNI must contain at least one Knight.
    }
    
    int impostor = -1;
    for (int person : KNI) {
        if (person == knight_ref) continue;
        if (query(person, knight_ref) == 0) {
            impostor = person;
            break;
        }
    }

    if (impostor == -1) {
        impostor = knight_ref;
    }
    
    std::cout << "! " << impostor << std::endl;
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