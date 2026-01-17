#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <random>
#include <chrono>

using namespace std;

typedef long long ll;

struct WordParams {
    int a, b, c;
};

// Function to calculate the number of distinct substrings of the concatenated string.
// The string structure is X^A O^B X^C O^D X^E.
// This corresponds to w_u (X^a O^b X^c) + w_v (X^d O^e X^f)
// where A=a, B=b, C=c+d, D=e, E=f.
// The formula counts distinct substrings based on which blocks they span.
ll calculate_power(int A, int B, int C, int D, int E) {
    ll res = 0;
    // Substrings contained within a single block of X's or O's
    res += max({A, C, E});
    res += max(B, D);
    
    // Substrings spanning 2 blocks:
    // Type XO: Spanning block 1-2 (X^A O^B) or 3-4 (X^C O^D).
    // Count is area of union of rectangles [1..A]x[1..B] and [1..C]x[1..D].
    res += (ll)A * B + (ll)C * D - (ll)min(A, C) * min(B, D);
    
    // Type OX: Spanning block 2-3 (O^B X^C) or 4-5 (O^D X^E).
    res += (ll)B * C + (ll)D * E - (ll)min(B, D) * min(C, E);
    
    // Substrings spanning 3 blocks:
    // Type XOX: Spanning 1-2-3 (X^u O^B X^v) or 3-4-5 (X^u O^D X^v).
    // If B != D, these sets are disjoint because they contain different number of O's.
    if (B != D) {
        res += (ll)A * C + (ll)C * E;
    } else {
        res += (ll)A * C + (ll)C * E - (ll)min(A, C) * min(C, E);
    }
    
    // Type OXO: Spanning 2-3-4 (O^u X^C O^v).
    res += (ll)B * D;
    
    // Substrings spanning 4 blocks:
    // Type XOXO: Spanning 1-2-3-4 (X^u O^B X^C O^v).
    res += (ll)A * D;
    
    // Type OXOX: Spanning 2-3-4-5 (O^u X^C O^D X^v).
    res += (ll)B * E;
    
    // Substrings spanning 5 blocks:
    // Type XOXOX: Spanning 1-2-3-4-5 (X^u O^B X^C O^D X^v).
    res += (ll)A * E;
    
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    vector<WordParams> words(n + 1);
    map<ll, pair<int, int>> power_map;
    
    // Random number generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    // To ensure asymmetry and reduce collisions, we assign distinct 'b' values for each word.
    // 'b' corresponds to the length of the middle 'O' block in w_i = X^a O^b X^c.
    vector<int> b_values(n);
    for(int i=0; i<n; ++i) b_values[i] = 1000 + i;
    shuffle(b_values.begin(), b_values.end(), rng);
    
    // Ranges for 'a' and 'c'
    uniform_int_distribution<int> dist_ac(100, 400);

    // Incremental construction
    for (int i = 1; i <= n; ++i) {
        bool valid = false;
        while (!valid) {
            int a = dist_ac(rng);
            int c = dist_ac(rng);
            int b = b_values[i-1];
            
            bool ok = true;
            vector<pair<ll, pair<int, int>>> temp_powers;
            
            // Check collisions with all pairs involving previously finalized words
            for (int j = 1; j < i; ++j) {
                // Pair (j, i) -> w_j then w_i
                // w_j = X^aj O^bj X^cj, w_i = X^a O^b X^c
                // Concatenation: X^aj O^bj X^(cj+a) O^b X^c
                ll p1 = calculate_power(words[j].a, words[j].b, words[j].c + a, b, c);
                if (power_map.count(p1)) { ok = false; break; }
                for(auto& tp : temp_powers) if(tp.first == p1) { ok = false; break; }
                if(!ok) break;
                temp_powers.push_back({p1, {j, i}});
                
                // Pair (i, j) -> w_i then w_j
                // Concatenation: X^a O^b X^(c+aj) O^bj X^cj
                ll p2 = calculate_power(a, b, c + words[j].a, words[j].b, words[j].c);
                if (power_map.count(p2)) { ok = false; break; }
                for(auto& tp : temp_powers) if(tp.first == p2) { ok = false; break; }
                if(!ok) break;
                temp_powers.push_back({p2, {i, j}});
            }
            if (!ok) continue;
            
            // Check pair (i, i)
            ll p_self = calculate_power(a, b, c + a, b, c);
            if (power_map.count(p_self)) { ok = false; }
            for(auto& tp : temp_powers) if(tp.first == p_self) { ok = false; break; }
            if(!ok) continue;
            
            // If all checks pass, commit this word
            words[i] = {a, b, c};
            power_map[p_self] = {i, i};
            for (auto& p : temp_powers) {
                power_map[p.first] = p.second;
            }
            valid = true;
        }
    }

    // Output the n words
    for (int i = 1; i <= n; ++i) {
        string s = "";
        s += string(words[i].a, 'X');
        s += string(words[i].b, 'O');
        s += string(words[i].c, 'X');
        cout << s << "\n";
    }
    cout.flush();

    // Answer queries
    int q;
    cin >> q;
    while (q--) {
        ll p;
        cin >> p;
        if (power_map.count(p)) {
            cout << power_map[p].first << " " << power_map[p].second << "\n";
        } else {
            // This case should not be reached with valid input
            cout << "1 1\n"; 
        }
        cout.flush();
    }

    return 0;
}