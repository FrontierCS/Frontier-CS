#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string s;
    if (!(cin >> s)) return 0;

    int n = (int)s.length();
    
    // Parse the string to count consecutive zeros between ones.
    // z[0] is the number of zeros before the first '1'.
    // z[i] is the number of zeros between the i-th and (i+1)-th '1'.
    // z[ones_count] is the number of zeros after the last '1'.
    vector<int> z;
    z.reserve(n + 1); // Maximum possible size
    
    int current_zeros = 0;
    int ones_count = 0;
    for (char c : s) {
        if (c == '0') {
            current_zeros++;
        } else {
            z.push_back(current_zeros);
            current_zeros = 0;
            ones_count++;
        }
    }
    z.push_back(current_zeros);

    // If there are no ones, no substring can satisfy count('0') = count('1')^2 unless count('1')=0.
    // Substrings with 0 ones must have 0 zeros (0 = 0^2), which implies empty string.
    // Typically non-empty substrings are required, and non-empty substrings with 0 ones have >0 zeros.
    // Thus, if ones_count == 0, the answer is 0.
    if (ones_count == 0) {
        cout << 0 << "\n";
        return 0;
    }

    // Precompute prefix sums of the zero counts to quickly calculate internal zeros for any window of ones.
    // P[i] stores the sum of z[0]...z[i-1].
    int m = (int)z.size();
    vector<int> P(m + 1, 0);
    for (int i = 0; i < m; ++i) {
        P[i+1] = P[i] + z[i];
    }

    long long ans = 0;
    int total_zeros = n - ones_count;
    
    // Iterate over the possible number of '1's (k) in the substring.
    // The condition is num_zeros = k^2.
    // k is bounded by ones_count and also k^2 <= total_zeros.
    for (int k = 1; k <= ones_count; ++k) {
        long long k2_long = (long long)k * k;
        if (k2_long > total_zeros) break; 
        
        int k2 = (int)k2_long;
        
        // We consider all contiguous groups of k ones.
        // A group starts at the x-th one (0-indexed) and ends at the (x+k-1)-th one.
        // There are ones_count - k + 1 such groups.
        int num_windows = ones_count - k + 1;
        
        for (int x = 0; x < num_windows; ++x) {
            // Calculate the number of zeros strictly inside the window of k ones.
            // These zeros are located in the gaps z[x+1], ..., z[x+k-1].
            // Using prefix sums, this is P[x+k] - P[x+1].
            int z_in = P[x+k] - P[x+1];
            
            // We need the total zeros to be k^2.
            // Let u be zeros taken from the gap immediately to the left (z[x]).
            // Let v be zeros taken from the gap immediately to the right (z[x+k]).
            // We need z_in + u + v = k^2  =>  u + v = k^2 - z_in.
            int S = k2 - z_in;
            
            // If S < 0, even with 0 external zeros, we have too many internal zeros.
            if (S >= 0) {
                int A = z[x];     // Max zeros available on left
                int B = z[x+k];   // Max zeros available on right
                
                // We need to count pairs (u, v) such that u + v = S
                // subject to 0 <= u <= A and 0 <= v <= B.
                // From v = S - u, we get 0 <= S - u <= B  =>  S - B <= u <= S.
                // Combining with 0 <= u <= A, we get:
                // max(0, S - B) <= u <= min(A, S).
                
                int low = S - B; 
                if (low < 0) low = 0;
                
                int high = A;
                if (S < high) high = S;
                
                if (high >= low) {
                    ans += (high - low + 1);
                }
            }
        }
    }

    cout << ans << "\n";

    return 0;
}