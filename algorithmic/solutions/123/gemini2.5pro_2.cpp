#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

// Function to print a query for a given set S
void ask_query(const std::vector<int>& s) {
    std::cout << "? " << s.size();
    for (int x : s) {
        std::cout << " " << x;
    }
    std::cout << std::endl;
}

// Function to print a guess
void make_guess(int g) {
    std::cout << "! " << g << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    // P: set of candidates assuming the last answer was true
    // Q: set of candidates assuming the last answer was false
    std::vector<int> p(n);
    std::iota(p.begin(), p.end(), 1);
    std::vector<int> q;

    // We can solve for x if the total number of candidates is at most 2, using our 2 guesses.
    // The loop reduces the candidate sets until they are small enough.
    while (p.size() + q.size() > 2) {
        // Split P and Q into two halves to construct the query set S.
        size_t pA_size = p.size() / 2;
        size_t qA_size = q.size() / 2;
        
        std::vector<int> s;
        // The query set S is formed by taking the first half of P and the first half of Q.
        if (pA_size > 0) {
            s.insert(s.end(), p.begin(), p.begin() + pA_size);
        }
        if (qA_size > 0) {
            s.insert(s.end(), q.begin(), q.begin() + qA_size);
        }
        
        // The loop condition |P|+|Q| > 2 ensures S will be non-empty.
        ask_query(s);
        std::string response;
        std::cin >> response;

        // Create the partitions of P and Q to be used for constructing the next state.
        std::vector<int> pA(p.begin(), p.begin() + pA_size);
        std::vector<int> pB(p.begin() + pA_size, p.end());
        std::vector<int> qA(q.begin(), q.begin() + qA_size);
        std::vector<int> qB(q.begin() + qA_size, q.end());
        
        std::vector<int> next_p, next_q;
        if (response == "YES") {
            // New P: candidates from old P and Q that are in S.
            next_p.reserve(pA.size() + qA.size());
            next_p.insert(next_p.end(), pA.begin(), pA.end());
            next_p.insert(next_p.end(), qA.begin(), qA.end());
            // New Q: candidates from old P that are NOT in S.
            next_q = pB;
        } else { // NO
            // New P: candidates from old P and Q NOT in S.
            next_p.reserve(pB.size() + qB.size());
            next_p.insert(next_p.end(), pB.begin(), pB.end());
            next_p.insert(next_p.end(), qB.begin(), qB.end());
            // New Q: candidates from old P that ARE in S.
            next_q = pA;
        }
        p = std::move(next_p);
        q = std::move(next_q);
    }

    // Once the total number of candidates is 2 or less, make guesses.
    std::vector<int> final_candidates;
    final_candidates.insert(final_candidates.end(), p.begin(), p.end());
    final_candidates.insert(final_candidates.end(), q.begin(), q.end());
    
    for (int candidate : final_candidates) {
        make_guess(candidate);
        std::string response;
        std::cin >> response;
        if (response == ":)") {
            return 0;
        }
    }

    return 0;
}