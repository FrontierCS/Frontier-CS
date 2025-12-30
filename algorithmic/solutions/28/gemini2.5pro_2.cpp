#include <iostream>
#include <vector>
#include <string>
#include <set>
#include <algorithm>

void solve() {
    int n;
    std::cin >> n;

    std::set<std::string> found_words;
    
    for (char c = 'a'; c <= 'z'; ++c) {
        if (found_words.size() == n) {
            break;
        }
        
        std::string prefix(1, c);
        int k = 1;
        
        while (true) {
            if (found_words.size() == n) {
                break;
            }

            std::cout << "query " << prefix << " " << k << std::endl;
            
            int k_recv;
            std::cin >> k_recv;
            
            for (int i = 0; i < k_recv; ++i) {
                std::string word;
                std::cin >> word;
                found_words.insert(word);
            }
            
            if (k_recv < k) {
                break;
            }
            
            if (k == n) {
                break;
            }
            
            k *= 2;
            if (k > n) {
                k = n;
            }
        }
    }
    
    std::cout << "answer";
    for (const auto& word : found_words) {
        std::cout << " " << word;
    }
    std::cout << std::endl;
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