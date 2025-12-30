#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

using namespace std;

typedef long long ll;

ll gcd(ll a, ll b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

int main() {
    ll n;
    if (!(cin >> n)) return 0;

    ll max_score = -1;
    vector<ll> best_seq;

    // Strategy 1: Subsequence of i*(i+1)
    {
        vector<ll> s;
        // Generate base sequence
        for (ll i = 1; ; ++i) {
            ll val = i * (i + 1);
            if (val > n) break;
            s.push_back(val);
            if (s.size() > 2000000) break; 
        }

        if (!s.empty()) {
            vector<ll> current_seq;
            current_seq.push_back(s[0]);
            if (s.size() > 1) {
                current_seq.push_back(s[1]);
                ll cur_g = gcd(s[1], s[0]);
                
                for (size_t k = 2; k < s.size(); ++k) {
                    if (current_seq.size() >= 1000000) break;
                    ll val = s[k];
                    ll g = gcd(val, current_seq.back());
                    if (g > cur_g) {
                        current_seq.push_back(val);
                        cur_g = g;
                    }
                }
            }
            
            // Scaling
            if (!current_seq.empty()) {
                ll k = current_seq.size();
                ll last = current_seq.back();
                ll scale = n / last;
                if (scale < 1) scale = 1; 
                
                ll current_sum = 0;
                // Sum without scale first to avoid overflow if possible, 
                // but we need to compute score. 
                // However, sum a_i can exceed 2^63. We need __int128 for score calc.
                __int128 total_sum = 0;
                for(auto &x : current_seq) {
                    x *= scale;
                    total_sum += x;
                }
                
                __int128 score = total_sum * k;
                if (score > max_score) {
                    max_score = (ll)score; // Comparison only roughly needed if max_score fits in ll, otherwise logic needed
                    // Actually score can exceed 2^63.
                    // Let's store best score as __int128 or double.
                    // But here we just update.
                    best_seq = current_seq;
                }
            }
        }
    }

    // Strategy 2: Powers of 2 (good for small N)
    {
        vector<ll> s;
        ll val = 1;
        while (val <= n) {
            s.push_back(val);
            if (n / 2 < val) break;
            val *= 2;
        }
        // Powers of 2: 1, 2, 4, 8...
        // GCDs: 1, 2, 4... Strictly increasing.
        // It is a valid sequence itself.
        if (!s.empty()) {
            // Check if we can improve by scaling
            // For powers of 2, best scale is usually n / last
            ll k = s.size();
            ll last = s.back();
            ll scale = n / last;
            __int128 total_sum = 0;
            vector<ll> temp = s;
            for(auto &x : temp) {
                x *= scale;
                total_sum += x;
            }
            __int128 score = total_sum * k;
            
            // We need a proper comparison variable for score
            static __int128 global_max_score = -1;
            if (first_run) {
                 // Calculate score of first strategy
                 __int128 s1 = 0;
                 for(auto x : best_seq) s1 += x;
                 s1 *= best_seq.size();
                 global_max_score = s1;
                 first_run = false;
            }
            
            if (score > global_max_score) {
                global_max_score = score;
                best_seq = temp;
            }
        }
    }
    
    // Strategy 3: Greedy with small divisors
    // Only feasible for small N or short sequences, 
    // but the polynomial strategy covers large N better.
    // For safety, we rely on Strategy 1 for large N.

    // Output
    cout << best_seq.size() << "\n";
    for (size_t i = 0; i < best_seq.size(); ++i) {
        cout << best_seq[i] << (i == best_seq.size() - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}

// Global variable workaround for the lambda/block scope issue
namespace {
    bool first_run = true;
}