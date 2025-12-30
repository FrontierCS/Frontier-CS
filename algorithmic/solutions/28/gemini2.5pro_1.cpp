#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <set>

void solve() {
    int n;
    std::cin >> n;

    if (n == 0) {
        std::cout << "answer" << std::endl;
        std::cout.flush();
        return;
    }

    std::vector<std::string> initial_prefixes;
    std::set<std::string> found_words;

    for (char c = 'a'; c <= 'z'; ++c) {
        std::string prefix(1, c);
        std::cout << "query " << prefix << " " << 1 << std::endl;
        std::cout.flush();

        int k;
        std::cin >> k;
        if (k > 0) {
            initial_prefixes.push_back(prefix);
            std::string word;
            std::cin >> word;
            found_words.insert(word);
        }
    }
    
    // Process prefixes in reverse alphabetical order as a heuristic
    std::sort(initial_prefixes.rbegin(), initial_prefixes.rend());

    int n_rem = n;
    
    for (size_t i = 0; i < initial_prefixes.size(); ++i) {
        const std::string& prefix = initial_prefixes[i];
        
        int known_for_prefix = 0;
        for (const auto& word : found_words) {
            if (word.rfind(prefix, 0) == 0) {
                known_for_prefix++;
            }
        }
        
        int query_k = n - (found_words.size() - known_for_prefix);
        if (i == initial_prefixes.size() - 1) {
            // For the last prefix, we know exactly how many words are left
            query_k = n - found_words.size() + known_for_prefix;
        }

        if (query_k <= 0) continue;

        std::cout << "query " << prefix << " " << query_k << std::endl;
        std::cout.flush();
        
        int k;
        std::cin >> k;
        for (int j = 0; j < k; ++j) {
            std::string word;
            std::cin >> word;
            found_words.insert(word);
        }
    }

    std::cout << "answer";
    for (const auto& word : found_words) {
        std::cout << " " << word;
    }
    std::cout << std::endl;
    std::cout.flush();
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}