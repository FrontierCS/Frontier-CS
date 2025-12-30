#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>

// Finite field arithmetic
namespace FF {
    int Q;
    int P, K;
    std::vector<int> LOG, EXP;
    std::vector<std::vector<int>> MUL_TABLE, ADD_TABLE;

    void build_tables(int p, int k) {
        P = p; K = k;
        Q = 1;
        for (int i = 0; i < K; ++i) Q *= P;

        if (K == 1) { // Prime field
            ADD_TABLE.assign(Q, std::vector<int>(Q));
            MUL_TABLE.assign(Q, std::vector<int>(Q));
            for(int i = 0; i < Q; ++i) {
                for (int j = 0; j < Q; ++j) {
                    ADD_TABLE[i][j] = (i + j) % Q;
                    MUL_TABLE[i][j] = (i * j) % Q;
                }
            }
            return;
        }

        std::vector<int> ir_poly;
        if (Q == 4) ir_poly = {1, 1, 1}; // x^2+x+1
        else if (Q == 8) ir_poly = {1, 1, 0, 1}; // x^3+x+1
        else if (Q == 9) ir_poly = {2, 1, 1}; // x^2+x+2
        else if (Q == 16) ir_poly = {1, 1, 0, 0, 1}; // x^4+x+1

        // Represent elements as integers 0..Q-1, but internally map to polynomials for setup
        std::vector<std::vector<int>> poly_rep(Q, std::vector<int>(K));
        for(int i=0; i<Q; ++i) {
            int temp = i;
            for(int j=0; j<K; ++j) {
                poly_rep[i][j] = temp % P;
                temp /= P;
            }
        }
        
        // Find a generator 'g' (primitive element)
        int g = -1;
        for (int i=1; i<Q; ++i) {
             std::vector<int> powers(Q, 0);
             int current = 1;
             bool ok = true;
             for(int j=0; j<Q-1; ++j) {
                if(powers[current]) { ok = false; break; }
                powers[current] = 1;

                // Multiply current by i (as polynomials)
                std::vector<int> p1 = poly_rep[current];
                std::vector<int> p2 = poly_rep[i];
                std::vector<int> res(2*K - 1, 0);
                for(int a=0; a<K; ++a) for(int b=0; b<K; ++b) res[a+b] = (res[a+b] + p1[a]*p2[b])%P;

                for(int a=2*K-2; a>=K; --a) {
                    if(res[a] == 0) continue;
                    int factor = res[a];
                    for(int b=0; b<K+1; ++b) res[a-K+b] = (res[a-K+b] - factor*ir_poly[b]%P + P)%P;
                }
                
                int next_val = 0;
                for(int a=K-1; a>=0; --a) next_val = next_val*P + res[a];
                current = next_val;
             }
             if(ok && current == 1) { g = i; break; }
        }


        LOG.assign(Q, 0);
        EXP.assign(Q, 0);
        
        int current = 1;
        for(int i=0; i<Q-1; ++i) {
            EXP[i] = current;
            LOG[current] = i;
            
            // Multiply current by g
            std::vector<int> p1 = poly_rep[current];
            std::vector<int> p2 = poly_rep[g];
            std::vector<int> res(2*K-1, 0);
            for(int a=0; a<K; ++a) for(int b=0; b<K; ++b) res[a+b] = (res[a+b] + p1[a]*p2[b])%P;
            for(int a=2*K-2; a>=K; --a) {
                if(res[a] == 0) continue;
                int factor = res[a];
                for(int b=0; b<K+1; ++b) res[a-K+b] = (res[a-K+b] - factor*ir_poly[b]%P + P)%P;
            }
            int next_val = 0;
            for(int a=K-1; a>=0; --a) next_val = next_val*P + res[a];
            current = next_val;
        }

        ADD_TABLE.assign(Q, std::vector<int>(Q));
        MUL_TABLE.assign(Q, std::vector<int>(Q));
        for (int i = 0; i < Q; ++i) {
            for (int j = 0; j < Q; ++j) {
                std::vector<int> p1 = poly_rep[i];
                std::vector<int> p2 = poly_rep[j];
                int add_val = 0;
                for(int l=K-1; l>=0; --l) add_val = add_val*P + (p1[l]+p2[l])%P;
                ADD_TABLE[i][j] = add_val;
                if (i == 0 || j == 0) {
                    MUL_TABLE[i][j] = 0;
                } else {
                    MUL_TABLE[i][j] = EXP[(LOG[i] + LOG[j]) % (Q - 1)];
                }
            }
        }
    }
    
    int add(int a, int b) { return ADD_TABLE[a][b]; }
    int mul(int a, int b) { return MUL_TABLE[a][b]; }
}


bool is_prime(int n) {
    if (n <= 1) return false;
    for (int i = 2; i * i <= n; ++i) {
        if (n % i == 0) return false;
    }
    return true;
}

std::pair<int, int> get_prime_power_base(int q) {
    if (q <= 1) return {-1, -1};
    if (is_prime(q)) return {q, 1};
    for (int p = 2; p * p <= q; ++p) {
        if (q % p == 0) {
            long long val = p;
            int k = 1;
            while (val < q) {
                val *= p;
                k++;
            }
            if (val == q) return {p, k};
            else return {-1, -1};
        }
    }
    return {-1, -1};
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    long long n, m;
    std::cin >> n >> m;

    bool swapped = false;
    if (n > m) {
        std::swap(n, m);
        swapped = true;
    }

    std::vector<std::pair<int, int>> star_points;
    if (n + m - 1 > 0) {
        for (int j = 1; j <= m; ++j) {
            star_points.push_back({1, j});
        }
        for (int i = 2; i <= n; ++i) {
            star_points.push_back({i, 1});
        }
    }
    
    int best_q = -1;
    long long max_k_affine = 0;

    int q_limit = sqrt(n);
    for (int q = q_limit; q >= 2; --q) {
        if ((long long)q * q <= n && (long long)q * q + q <= m) {
            auto pk = get_prime_power_base(q);
            if (pk.first != -1) {
                long long k = (long long)q * q * q + (long long)q * q;
                if (k > max_k_affine) {
                    max_k_affine = k;
                    best_q = q;
                }
            }
        }
    }

    if (max_k_affine > star_points.size()) {
        int q = best_q;
        auto pk = get_prime_power_base(q);
        FF::build_tables(pk.first, pk.second);
        
        std::vector<std::pair<int, int>> affine_points;
        affine_points.reserve(max_k_affine);

        for (int i = 0; i < q * q; ++i) {
            int x = i / q;
            int y = i % q;
            for (int j = 0; j < q * q + q; ++j) {
                if (j < q * q) {
                    int a = j / q;
                    int b = j % q;
                    if (y == FF::add(FF::mul(a, x), b)) {
                        affine_points.push_back({i + 1, j + 1});
                    }
                } else {
                    int c = j - q * q;
                    if (x == c) {
                        affine_points.push_back({i + 1, j + 1});
                    }
                }
            }
        }
        
        std::cout << affine_points.size() << "\n";
        for (const auto& p : affine_points) {
            if (swapped) {
                std::cout << p.second << " " << p.first << "\n";
            } else {
                std::cout << p.first << " " << p.second << "\n";
            }
        }
    } else {
        std::cout << star_points.size() << "\n";
        for (const auto& p : star_points) {
            if (swapped) {
                std::cout << p.second << " " << p.first << "\n";
            } else {
                std::cout << p.first << " " << p.second << "\n";
            }
        }
    }

    return 0;
}