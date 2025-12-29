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
    string chars = "abcdefghijklmnopqrstuvwxyz";

    // Iterate through each possible starting character
    for (char c : chars) {
        // If we have already found all N words, we can stop immediately
        if (found_words.size() == (size_t)N) break;

        int k = 1;
        while (true) {
            // Check again before query to minimize cost
            if (found_words.size() == (size_t)N) break;
            
            // Query for 'k' words starting with prefix 'c'
            cout << "query " << c << " " << k << endl;
            
            int count;
            cin >> count;
            
            for (int i = 0; i < count; ++i) {
                string s;
                cin >> s;
                found_words.insert(s);
            }

            // If the service returned fewer words than requested (count < k),
            // it means we have retrieved all existing words starting with 'c'.
            if (count < k) {
                break;
            }
            
            // Otherwise, double k and query again to ensure we get all words.
            // This doubling strategy ensures the total sum of K is within the 4N limit.
            k *= 2;
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
    // Optimize I/O operations slightly, though not strictly necessary for this interactive problem.
    // We do NOT untie cin from cout to ensure proper flushing semantics if we were using raw cin/cout,
    // but here we use endl which forces flush.
    ios_base::sync_with_stdio(false);
    
    int T;
    if (cin >> T) {
        while (T--) {
            solve();
        }
    }
    return 0;
}