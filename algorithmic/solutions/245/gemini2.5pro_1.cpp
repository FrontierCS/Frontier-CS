#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>

using namespace std;

// Wrapper for asking a query to the interactor
int ask(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int response;
    cin >> response;
    if (response == -1) exit(0);
    return response;
}

// Wrapper for providing the final answer
void answer(int x) {
    cout << "! " << x << endl;
}

void solve() {
    int n;
    cin >> n;

    // Phase 1: Reduce the set of candidates for Impostor.
    // A (Knight, Knave) pair will accuse each other.
    // If ask(i, j) == 0 and ask(j, i) == 0, then {i, j} is a {Knight, Knave} pair.
    // Neither can be the Impostor. We can eliminate them.
    // We group players and try to find such pairs to eliminate.
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    while (candidates.size() > 2) {
        vector<int> next_candidates;
        // Process in groups of 3. For each group, we hope to eliminate 2.
        for (size_t i = 0; i + 2 < candidates.size(); i += 3) {
            int p1 = candidates[i];
            int p2 = candidates[i+1];
            int p3 = candidates[i+2];

            int res12 = ask(p1, p2);
            int res21 = ask(p2, p1);

            if (res12 == 0 && res21 == 0) { // {p1, p2} is a {K, V} pair.
                next_candidates.push_back(p3);
            } else {
                int res23 = ask(p2, p3);
                int res32 = ask(p3, p2);
                if (res23 == 0 && res32 == 0) { // {p2, p3} is a {K, V} pair.
                    next_candidates.push_back(p1);
                } else {
                    // We can't be certain about p1,p2,p3. Keep them all.
                    // An adaptive grader might force this path.
                    // To be safe, we must consider all of them potential impostors.
                    next_candidates.push_back(p1);
                    next_candidates.push_back(p2);
                    next_candidates.push_back(p3);
                }
            }
        }
        // Add leftover players
        for (size_t i = (candidates.size() / 3) * 3; i < candidates.size(); ++i) {
            next_candidates.push_back(candidates[i]);
        }
        if (next_candidates.size() == candidates.size()) {
            // No reduction happened, pairing won't work. Break and handle remaining.
            break;
        }
        candidates = next_candidates;
    }
    
    // Phase 2: We have a small set of candidates. We need to find the Impostor among them.
    // First, find a player who is definitely a Knight.
    // A player `c` who is a sink in the "accuses" graph (A(i,j)=0) must be a Knight or Impostor.
    // This is because if `c` were a Knave, all Knights would accuse `c`.
    // Let's find such a candidate.
    vector<int> all_players(n);
    iota(all_players.begin(), all_players.end(), 1);

    int sink_cand = all_players[0];
    for (size_t i = 1; i < all_players.size(); ++i) {
        if (ask(sink_cand, all_players[i]) == 0) { // sink_cand accuses all_players[i]
            // sink_cand remains a candidate for sink
        } else { // sink_cand vouches for all_players[i], so sink_cand is not a sink.
            sink_cand = all_players[i];
        }
    }
    
    // Verify if sink_cand is actually a sink.
    // And also check if it could be an Impostor. An Impostor is not a sink because they accuse Knights.
    // A true sink must be a Knight.
    int knight = -1;
    bool is_sink = true;
    int vouched_for_count = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == sink_cand) continue;
        if (ask(i, sink_cand) == 1) {
            vouched_for_count++;
        }
    }
    
    // A Knight is vouched for by all other Knights and the Impostor.
    // A Knave is vouched for by all other Knaves.
    // An Impostor is vouched for by all Knights.
    // Number of Knights is > 0.3*n.
    // If sink_cand is vouched for by everyone (n-1 players), they must be K/I.
    if (vouched_for_count == n - 1) { // Everyone says sink_cand is K/I.
        // This means sink_cand is K or I.
        // If sink_cand is K, it vouches for other K and I.
        // If sink_cand is I, it vouches for V.
        // If it's a Knight, it should vouch for >0.3*n other players.
        // If it's an Impostor, it vouches for all Knaves, <0.7*n. This is ambiguous.
        // But we have another candidate from our reduction.
        if (candidates.size() == 1) impostor_cand = candidates[0];
        else if (candidates.size() == 2) { // if both are in this vouched for group, pick one. else pick the one not vouched for.
            int p1 = candidates[0], p2 = candidates[1];
            if (p1 == sink_cand) impostor_cand = p1;
            else if (p2 == sink_cand) impostor_cand = p2;
            else { // a contradiction. Maybe our reduction was wrong. Heuristic: pick one.
                impostor_cand = p1;
            }
        }
        else { // reduction failed, pick sink_cand
            impostor_cand = sink_cand;
        }
        answer(impostor_cand);
        return;
    }
    
    // Find a knight by assuming sink_cand is a liar, as it's not a sink.
    // The player who accused sink_cand could be a knight.
    // This gets complicated. A simpler final step:
    // We have a small list of candidates. Identify K/I group and find Impostor.
    int p = candidates[0];
    vector<int> pk_group;
    pk_group.push_back(p);
    for (int i=1; i<=n; ++i) {
        if (i == p) continue;
        if (ask(p, i) == 1) {
            pk_group.push_back(i);
        }
    }

    if (pk_group.size() <= floor(0.3 * n)) {
        vector<int> real_pk_group;
        vector<bool> is_in_pk(n + 1, false);
        for(int person : pk_group) is_in_pk[person] = true;
        for(int i=1; i<=n; ++i) if(!is_in_pk[i]) real_pk_group.push_back(i);
        pk_group = real_pk_group;
    }

    while(pk_group.size() > 1) {
        int p1 = pk_group.back(); pk_group.pop_back();
        int p2 = pk_group.back(); pk_group.pop_back();
        if (ask(p1,p2) == 0) { // p1 accuses p2. p1 is Impostor, p2 is Knight
             pk_group.push_back(p1);
        } else { // p1 vouches p2. p1 is Knight, p2 is K/I
             pk_group.push_back(p2);
        }
    }
    answer(pk_group[0]);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}