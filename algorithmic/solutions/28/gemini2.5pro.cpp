#include <iostream>
#include <vector>
#include <string>
#include <set>
#include <algorithm>

// Function to solve a single test case
void solve() {
    int n;
    std::cin >> n;

    std::set<std::string> found_words;

    // Iterate through all possible starting letters
    for (char c = 'a'; c <= 'z'; ++c) {
        if (found_words.size() == n) {
            break;
        }

        std::string prefix(1, c);
        int k_to_ask = 1;

        // Exponentially probe for the number of words with the current prefix
        while (true) {
            if (found_words.size() == n) {
                break;
            }

            std::cout << "query " << prefix << " " << k_to_ask << std::endl;

            int k_returned;
            std::cin >> k_returned;

            for (int i = 0; i < k_returned; ++i) {
                std::string word;
                std::cin >> word;
                found_words.insert(word);
            }

            if (k_returned < k_to_ask) {
                // If fewer words are returned than requested, we have found all for this prefix
                break;
            }
            
            if (k_to_ask == n) {
                // If we ask for n and get n, we must have all words for this prefix
                // as there are only n words in total.
                break;
            }

            // Double the number of words to ask for in the next query
            k_to_ask *= 2;
            if (k_to_ask > n) {
                k_to_ask = n;
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