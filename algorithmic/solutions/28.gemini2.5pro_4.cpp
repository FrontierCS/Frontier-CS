#include <iostream>
#include <vector>
#include <string>
#include <set>
#include <algorithm>

// Function to solve a single test case
void solve() {
    int n;
    std::cin >> n;

    // Use a set to store unique words found
    std::set<std::string> found_words;

    // Iterate through all possible first letters
    for (char c = 'a'; c <= 'z'; ++c) {
        // Small optimization: if all words are found, no need to query more
        if (found_words.size() == n) {
            break;
        }

        std::string prefix(1, c);
        long long k = 1;
        bool done_with_prefix = false;

        // Use exponential search for the number of words with this prefix
        while (!done_with_prefix) {
            // Make a query
            std::cout << "query " << prefix << " " << k << std::endl;

            // Read the response
            int count;
            std::cin >> count;
            for (int i = 0; i < count; ++i) {
                std::string word;
                std::cin >> word;
                found_words.insert(word);
            }

            // If the service returns fewer words than requested, we have found all
            // words with this prefix.
            if (count < k) {
                done_with_prefix = true;
            }

            // If we have already queried with K=N, we are guaranteed to have found
            // all words for this prefix, as there are at most N total words.
            if (k == n) {
                done_with_prefix = true;
            }

            // Prepare K for the next query if not done
            if (!done_with_prefix) {
                k *= 2;
                if (k > n) {
                    k = n;
                }
            }
        }
    }

    // Output the final answer
    std::cout << "answer";
    for (const auto& word : found_words) {
        std::cout << " " << word;
    }
    std::cout << std::endl;
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }

    return 0;
}