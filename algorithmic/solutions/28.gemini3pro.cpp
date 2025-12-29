#include <iostream>
#include <vector>
#include <string>
#include <set>
#include <algorithm>

using namespace std;

void solve() {
    int N;
    if (!(cin >> N)) return;

    // Use a set to store unique words found so far.
    // This also keeps them sorted, which is nice for the answer, though not strictly required by protocol (arbitrary order).
    set<string> found_words;
    
    // Iterate through each starting character 'a' through 'z'.
    for (char c = 'a'; c <= 'z'; ++c) {
        // If we have already found all N words, we can stop early.
        if (found_words.size() == N) break;

        string s(1, c);
        int local_found = 0; // Number of words starting with 'c' found so far
        int limit = 1;       // Current target for query size K

        while (found_words.size() < N) {
            // We implement an exponential search strategy (doubling limit) to find the number of words starting with 'c'.
            // If the current limit is less than or equal to what we already found, we need to increase it.
            if (limit <= local_found) {
                limit *= 2;
                continue;
            }

            // Calculate the maximum meaningful K we should ask for.
            // We know the total number of words is N.
            // We know the number of words found that do NOT start with 'c' is (found_words.size() - local_found).
            // Therefore, the maximum number of words starting with 'c' that could possibly exist is:
            // N - (found_words.size() - local_found).
            // Asking for more than this is wasteful.
            int other_found = found_words.size() - local_found;
            int remaining_possible_local = N - other_found;
            
            // K is the minimum of our doubling limit and the theoretical maximum needed.
            int K = min(limit, remaining_possible_local);
            
            // If the calculated K doesn't exceed what we already know, we must increase the limit.
            // This happens if remaining_possible_local is large but limit is still small.
            if (K <= local_found) {
                 limit *= 2; 
                 continue;
            }

            cout << "query " << s << " " << K << endl;

            int k;
            cin >> k;
            // The protocol guarantees k strings follow.
            for (int i = 0; i < k; ++i) {
                string w;
                cin >> w;
                found_words.insert(w);
            }
            
            local_found = k;

            // If the service returned fewer words than requested, we have found all words starting with 'c'.
            if (k < K) {
                break;
            }
            
            // If we have found all N words globally, we can stop.
            if (found_words.size() == N) break;

            // Otherwise, double the limit and continue to find more words starting with 'c'.
            limit *= 2;
        }
    }

    cout << "answer";
    for (const auto& w : found_words) {
        cout << " " << w;
    }
    cout << endl;
}

int main() {
    // The problem requires flushing output after each request.
    // std::endl flushes the stream, so using it is sufficient.
    int T;
    if (cin >> T) {
        while (T--) {
            solve();
        }
    }
    return 0;
}