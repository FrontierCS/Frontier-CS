#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

void ask_query(const std::vector<int>& s) {
    std::cout << "? " << s.size();
    for (int x : s) {
        std::cout << " " << x;
    }
    std::cout << std::endl;
}

void make_guess(int g) {
    std::cout << "! " << g << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<bool> p_cand(n + 1, false), m_cand(n + 1, false);
    int p_size = n, m_size = 0;
    for (int i = 1; i <= n; ++i) p_cand[i] = true;

    bool prev_ans_proven_lie = false;
    int guesses_left = 2;

    while (p_size + m_size > 2) {
        if (p_size == 0 && m_size > 0) {
            p_cand = m_cand;
            p_size = m_size;
            std::fill(m_cand.begin(), m_cand.end(), false);
            m_size = 0;
            prev_ans_proven_lie = true;
        }

        if (prev_ans_proven_lie) {
            std::vector<int> p_vec;
            for (int i = 1; i <= n; ++i) if (p_cand[i]) p_vec.push_back(i);
            
            std::vector<int> s;
            for (size_t i = 0; i < p_vec.size() / 2; ++i) s.push_back(p_vec[i]);
            
            if (s.empty() && !p_vec.empty()) s.push_back(p_vec[0]);
            if (s.empty()) break;
            
            ask_query(s);
            std::string ans;
            std::cin >> ans;

            std::vector<bool> s_mask(n + 1, false);
            for (int x : s) s_mask[x] = true;
            
            std::vector<bool> next_p_cand(n + 1, false);
            int next_p_size = 0;
            if (ans == "YES") {
                for (int x : s) {
                    if (p_cand[x]) {
                        next_p_cand[x] = true;
                        next_p_size++;
                    }
                }
            } else {
                for (int x : p_vec) {
                    if (!s_mask[x]) {
                        next_p_cand[x] = true;
                        next_p_size++;
                    }
                }
            }
            p_cand = next_p_cand;
            p_size = next_p_size;
            prev_ans_proven_lie = false;
            continue;
        }
        
        if (guesses_left > 0 && p_size == 1) {
            int g = -1;
            for (int i = 1; i <= n; ++i) if (p_cand[i]) { g = i; break; }
            make_guess(g);
            guesses_left--;
            std::string res;
            std::cin >> res;
            if (res == ":)") return 0;
            
            p_cand = m_cand;
            p_size = m_size;
            std::fill(m_cand.begin(), m_cand.end(), false);
            m_size = 0;
            if (p_cand[g]) {
                p_cand[g] = false;
                p_size--;
            }
            prev_ans_proven_lie = true;
            continue;
        }

        std::vector<int> p_vec, m_vec;
        for (int i = 1; i <= n; ++i) {
            if (p_cand[i]) p_vec.push_back(i);
            if (m_cand[i]) m_vec.push_back(i);
        }

        std::vector<int> s;
        for (size_t i = 0; i < p_vec.size() / 2; ++i) s.push_back(p_vec[i]);
        for (size_t i = 0; i < m_vec.size() / 2; ++i) s.push_back(m_vec[i]);
        
        if (s.empty()) {
             if (!p_vec.empty()) s.push_back(p_vec[0]);
             else if (!m_vec.empty()) s.push_back(m_vec[0]);
             else break; 
        }

        ask_query(s);
        std::string ans;
        std::cin >> ans;
        std::vector<bool> s_mask(n + 1, false);
        for (int x : s) s_mask[x] = true;
        
        std::vector<bool> p_new(n + 1, false), m_new(n + 1, false);
        int p_new_size = 0, m_new_size = 0;

        if (ans == "YES") {
            for (int i = 1; i <= n; ++i) {
                if (m_cand[i] && !s_mask[i]) continue; // forbidden
                if (p_cand[i] || m_cand[i]) {
                    if (s_mask[i]) {
                        p_new[i] = true;
                        p_new_size++;
                    } else {
                        m_new[i] = true;
                        m_new_size++;
                    }
                }
            }
        } else { // NO
            for (int i = 1; i <= n; ++i) {
                if (m_cand[i] && s_mask[i]) continue; // forbidden
                if (p_cand[i] || m_cand[i]) {
                    if (!s_mask[i]) {
                        p_new[i] = true;
                        p_new_size++;
                    } else {
                        m_new[i] = true;
                        m_new_size++;
                    }
                }
            }
        }
        p_cand = p_new;
        p_size = p_new_size;
        m_cand = m_new;
        m_size = m_new_size;
    }

    for (int i = 1; i <= n; ++i) {
        if (p_cand[i] || m_cand[i]) {
            make_guess(i);
            std::string res;
            std::cin >> res;
            if (res == ":)") return 0;
        }
    }
    return 0;
}