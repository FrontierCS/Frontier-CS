#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>

// Wrapper for the query to the interactor
int ask(int i, int j) {
    std::cout << "? " << i << " " << j << std::endl;
    int response;
    std::cin >> response;
    if (response == -1) exit(0);
    return response;
}

// Function to announce the answer
void answer(int x) {
    std::cout << "! " << x << std::endl;
}

void solve() {
    int n;
    std::cin >> n;

    std::vector<int> players(n);
    std::iota(players.begin(), players.end(), 1);

    // Phase 1: Reduce players to a smaller group of candidates.
    while (players.size() > 2) {
        std::vector<int> next_round_players;
        for (size_t i = 0; i + 2 < players.size(); i += 3) {
            int p1 = players[i];
            int p2 = players[i + 1];
            int p3 = players[i + 2];

            int r12 = ask(p1, p2);
            int r23 = ask(p2, p3);

            if (r12 == 1 && r23 == 1) { // Likely all same type (K,K,K) or (L,L,L)
                next_round_players.push_back(p1);
            } else if (r12 == 0 && r23 == 0) { // e.g., (K,V,K) or (L,K,L)
                next_round_players.push_back(p1);
            } else if (r12 == 1 && r23 == 0) { // e.g., (K,K,V) or (L,V,K)
                next_round_players.push_back(p2);
            } else { // r12 == 0 && r23 == 1, e.g., (K,V,L) or (L,K,K)
                next_round_players.push_back(p2);
            }
        }
        // Add remaining players if any
        if (players.size() % 3 != 0) {
            for (size_t i = (players.size() / 3) * 3; i < players.size(); ++i) {
                next_round_players.push_back(players[i]);
            }
        }
        players = next_round_players;
    }

    // Phase 2: Identify a Knight from the 1 or 2 remaining candidates.
    int p1 = players[0];
    int p2 = (players.size() > 1) ? players[1] : -1;
    
    int knight_cand = -1;
    if (p2 == -1) {
        knight_cand = p1;
    } else {
        if (ask(p1, p2) == 1) {
            knight_cand = p1;
        } else {
            knight_cand = p2;
        }
    }

    // Phase 3: Use candidate Knight to partition all players and verify.
    std::vector<int> ki_set_cand;
    for (int i = 1; i <= n; i++) {
        if (i == knight_cand) {
            continue;
        }
        if (ask(knight_cand, i) == 1) {
            ki_set_cand.push_back(i);
        }
    }
    ki_set_cand.push_back(knight_cand);
    
    int knight_min_count = floor(0.3 * n) + 1;
    if (ki_set_cand.size() < (size_t)knight_min_count + 1) {
        // Our 'knight' was a liar. The real KI_set are the ones who he said are Knaves, plus himself.
        std::vector<bool> is_in_ki_set(n + 1, false);
        for (int p : ki_set_cand) {
            is_in_ki_set[p] = true;
        }
        ki_set_cand.clear();
        for (int i = 1; i <= n; i++) {
            if (!is_in_ki_set[i]) {
                ki_set_cand.push_back(i);
            }
        }
         ki_set_cand.push_back(knight_cand); // Add the liar himself
    }
    
    // Phase 4: Find the Impostor within the confirmed KI set.
    while (ki_set_cand.size() > 1) {
        int cand1 = ki_set_cand.back();
        ki_set_cand.pop_back();
        int cand2 = ki_set_cand.back();
        
        if (ask(cand1, cand2) == 0) {
            // cand1 says cand2 is a Knave.
            // A Knight would never say this about another member of the KI set.
            // So, cand1 must be the Impostor.
            ki_set_cand.back() = cand2;
        } else {
            // cand1 says cand2 is a Knight/Impostor. This is consistent with cand1 being a Knight.
            // We keep cand1 as he is more likely to be a Knight.
             ki_set_cand.back() = cand1;
        }
    }

    answer(ki_set_cand[0]);
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