#include <iostream>
#include <vector>
#include <string>
#include <set>
#include <algorithm>

using namespace std;

// Function to count how many words in the 'found' set start with 'prefix'
int count_starts_with(const set<string>& found, const string& prefix) {
    int cnt = 0;
    for (const string& w : found) {
        if (w.size() >= prefix.size() && w.substr(0, prefix.size()) == prefix) {
            cnt++;
        }
    }
    return cnt;
}

void solve() {
    int N;
    if (!(cin >> N)) return;

    set<string> found_words;

    // Iterate through all possible starting characters.
    // Since we cannot query with empty string, we probe each starting character.
    for (char c = 'a'; c <= 'z'; ++c) {
        // If we have already found all N words, we can terminate early.
        if (found_words.size() == (size_t)N) break;

        string s(1, c);
        int K = 1;
        while (true) {
            // Count how many words starting with 'c' we already know.
            int known_c = count_starts_with(found_words, s);
            // Count how many words are still missing globally.
            int rem = N - found_words.size();
            
            if (rem == 0) break;

            // The maximum number of words starting with 's' that can possibly exist
            // is the number we already know starting with 's' plus all remaining unknown words
            // (assuming conservatively that all unknown words might start with 's').
            long long max_possible = (long long)known_c + rem;
            long long limit = K;
            bool clamped = false;
            
            // We clamp the query limit to avoid asking for more words than can possibly exist.
            // This is crucial to minimize the sum of K.
            if (limit >= max_possible) {
                limit = max_possible;
                clamped = true;
            }
            
            cout << "query " << s << " " << limit << endl;
            
            int k;
            cin >> k;
            
            for (int i = 0; i < k; ++i) {
                string w;
                cin >> w;
                found_words.insert(w);
            }

            // If the service returned fewer words than requested, we know we have retrieved all
            // words starting with this prefix.
            if (k < limit) {
                break;
            }
            // If we clamped our request to the maximum possible count and received exactly that many,
            // we effectively found all relevant words (since we assumed all remaining words start here).
            // Even if the prefix actually contains fewer words than limit, if we got 'limit' words,
            // we must have found all remaining unknown words.
            if (clamped && k == limit) {
                break;
            }
            
            // Exponentially increase K to find remaining words quickly.
            // Doubling strategy keeps the total cost proportional to 4 * N.
            K *= 2;
        }
    }

    cout << "answer";
    for (const string& w : found_words) {
        cout << " " << w;
    }
    cout << endl;
}

int main() {
    // The problem requires flushing output after each query, which endl does.
    int T;
    if (cin >> T) {
        while (T--) {
            solve();
        }
    }
    return 0;
}