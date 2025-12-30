#include <iostream>
#include <vector>
#include <string>
#include <set>
#include <algorithm>

using namespace std;

// Function to solve a single test case
void solve() {
    int N;
    if (!(cin >> N)) return;

    set<string> found_words;
    
    // Iterate through all possible starting characters 'a' through 'z'.
    // Since we cannot query with an empty string, we process each initial letter independently.
    for (char c = 'a'; c <= 'z'; ++c) {
        // If we have already found all N words, we can stop immediately.
        if (found_words.size() == N) break;

        string p(1, c);
        int known_p = 0; // Number of words starting with prefix p found so far
        int K = 1;       // Exponential search parameter for K

        while (true) {
            // Check if we are done globally
            if (found_words.size() == N) break;

            int needed = N - found_words.size();
            
            // The maximum number of words starting with p we could possibly find 
            // is the ones we already know plus all the remaining unknown words globally.
            // Requesting more than this is wasteful.
            int limit = known_p + needed;
            
            // We use the doubling strategy for K to find words efficiently, but clamp it to limit.
            int current_K = min(K, limit);
            
            // Ensure query K is at least 1 (though logic guarantees limit >= known_p + 1 >= 1)
            current_K = max(1, current_K);

            // Query the interactive system
            cout << "query " << p << " " << current_K << endl;
            
            int k_ret;
            cin >> k_ret;
            
            // Read the returned words
            for (int i = 0; i < k_ret; ++i) {
                string s;
                cin >> s;
                found_words.insert(s);
            }

            known_p = k_ret;

            // If we found everything, break out
            if (found_words.size() == N) break;

            // If the system returned fewer words than we asked for, 
            // it means there are no more words starting with prefix p.
            if (k_ret < current_K) {
                break;
            }

            // If we got exactly current_K words, there might be more.
            // Double the range to find the next batch efficiently.
            // This maintains a low total sum of K relative to N.
            K *= 2;
        }
    }

    // Output the answer
    cout << "answer";
    for (const string& s : found_words) {
        cout << " " << s;
    }
    cout << endl;
}

int main() {
    // Optimize I/O is not strictly necessary for interactive but good practice, 
    // however, we must ensure flushing. std::endl forces flush.
    
    int T;
    if (cin >> T) {
        while (T--) {
            solve();
        }
    }
    return 0;
}