#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Interactor communication functions
int ask(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int response;
    cin >> response;
    if (response == -1) {
        exit(0);
    }
    return response;
}

void answer(int i) {
    cout << "! " << i << endl;
}

void solve() {
    int n;
    cin >> n;

    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    // Phase 1: Reduce the set of candidates to 2.
    // We can remove one player from a group of 3 using 2 queries.
    // Take i,j,k. Ask k about i and j.
    // If k gives the same answer (0,0 or 1,1), it means i and j are of the "same type" from k's POV.
    // This implies i and j are either both Knaves, or both non-Knaves. k is the odd one out. Discard k.
    // If k gives different answers (0,1 or 1,0), i and j are of "different types".
    // k has successfully distinguished them. We can discard i and j and keep k.
    // This logic is complex with an adaptive grader. A simpler, more robust reduction:
    // repeatedly find a {Knight, Knave} pair, which are non-impostors, and remove them.
    
    vector<int> safe_kn_kv; // known non-impostors
    while(candidates.size() >= 2) {
        int p1 = candidates.back(); candidates.pop_back();
        if (candidates.empty()) {
            safe_kn_kv.push_back(p1);
            break;
        }
        int p2 = candidates.back(); candidates.pop_back();

        int res1 = ask(p1, p2);
        int res2 = ask(p2, p1);
        if (res1 == 0 && res2 == 0) {
            // {p1, p2} is a {Knight, Knave} pair. Neither can be the Impostor.
            // We don't need them further for now.
        } else {
            // At least one is not a simple Knight/Knave, or they are of the same type.
            // We can't be sure, so we put one back.
            safe_kn_kv.push_back(p1);
        }
    }
    
    // safe_kn_kv now contains all players that were not part of a {K,V} pair that we found.
    // The impostor must be in this set.
    candidates = safe_kn_kv;
    
    // Now, keep reducing until we have one candidate.
    // The classic Knight/Knave reduction:
    // If i says j is a Knight, i could be K (and j is K/I) or L (and j is V). i is less trustworthy.
    // If i says j is a Knave, i could be K (and j is V) or L (and j is K/I). i is more trustworthy.
    while (candidates.size() > 1) {
        int p1 = candidates.back(); candidates.pop_back();
        int p2 = candidates.back(); candidates.pop_back();
        if (ask(p1, p2) == 1) {
            candidates.push_back(p2);
        } else {
            candidates.push_back(p1);
        }
    }

    int impostor_candidate = candidates[0];
    
    // Now we have one candidate for the impostor.
    // Let's verify. If he is the impostor, he is a liar. The set of people he
    // claims are Knights are actually all Knaves.
    // If he is a Knight, the set of people he claims are Knights are Knights and the Impostor.
    vector<int> potential_knights;
    for (int i = 1; i <= n; ++i) {
        if (i == impostor_candidate) continue;
        if (ask(impostor_candidate, i) == 1) {
            potential_knights.push_back(i);
        }
    }

    // If impostor_candidate is a Knight, potential_knights are all K's + one I.
    // They will all vouch for each other (except I will accuse K).
    // If impostor_candidate is an Impostor, potential_knights are all V's.
    // They will all vouch for each other.
    // If impostor_candidate is a Knave, potential_knights are all other V's + I.
    // They will not all vouch for each other.
    
    // The impostor is the only one who is in a K/I group and accuses another member.
    // A knight in a K/I group vouches for everyone.
    
    potential_knights.push_back(impostor_candidate);
    
    while(potential_knights.size() > 1) {
        int p1 = potential_knights.back(); potential_knights.pop_back();
        int p2 = potential_knights.back(); potential_knights.pop_back();
        if (ask(p1, p2) == 0) { // p1 accuses p2.
            // If this is a group of K's and one I, p1 must be I and p2 must be K.
            potential_knights.push_back(p1);
        } else { // p1 vouches for p2.
            // p1 is likely K. p2 could be K or I.
            potential_knights.push_back(p2);
        }
    }
    
    answer(potential_knights[0]);

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