#include <iostream>
#include <vector>
#include <string>
#include <set>

using namespace std;

void solve() {
    int N;
    if (!(cin >> N)) return;

    set<string> found_words;
    
    // Iterate through all possible starting characters
    for (char c = 'a'; c <= 'z'; ++c) {
        // Optimization: If we have already found all N words, we don't need to search further.
        if (found_words.size() == N) break;

        int K = 1;
        string prefix(1, c);
        
        while (true) {
            cout << "query " << prefix << " " << K << endl;
            int k;
            cin >> k;
            
            for (int i = 0; i < k; ++i) {
                string s;
                cin >> s;
                found_words.insert(s);
            }
            
            // If the number of words returned is less than K, 
            // it means we have retrieved all words starting with this prefix.
            if (k < K) {
                break;
            }
            
            // If we found all N words globally, we can also stop searching this prefix.
            if (found_words.size() == N) {
                break;
            }

            // Double the limit for the next attempt (Geometric doubling strategy)
            K *= 2;
        }
    }

    cout << "answer";
    for (const auto& w : found_words) {
        cout << " " << w;
    }
    cout << endl;
}

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int T;
    if (cin >> T) {
        while (T--) {
            solve();
        }
    }
    return 0;
}