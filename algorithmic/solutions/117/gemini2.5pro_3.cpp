#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <algorithm>
#include <set>

// Use long double for high precision calculations
using LD = long double;

// A simple 2D vector structure
struct Vector2D {
    LD x, y;
};

// Function to send a query to the interactor and receive the result
LD query(LD x, LD y) {
    std::cout << "? " << std::fixed << std::setprecision(10) << x << " " << y << std::endl;
    LD dist_sum;
    std::cin >> dist_sum;
    return dist_sum;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N;
    std::cin >> N;

    // Phase 1: Find all slopes a_i
    const int GRID_SIZE = 20;
    const LD C = 2000.0;
    std::vector<std::vector<LD>> D(GRID_SIZE, std::vector<LD>(GRID_SIZE));

    // Query points on a grid. Total GRID_SIZE*GRID_SIZE queries.
    for (int i = 0; i < GRID_SIZE; ++i) {
        for (int j = 0; j < GRID_SIZE; ++j) {
            LD x = C * (i - (GRID_SIZE / 2 - 1));
            LD y = C * (j - (GRID_SIZE / 2 - 1));
            D[i][j] = query(x, y);
        }
    }

    // Compute gradients at the center of each grid cell
    std::vector<std::vector<Vector2D>> grads(GRID_SIZE - 1, std::vector<Vector2D>(GRID_SIZE - 1));
    for (int i = 0; i < GRID_SIZE - 1; ++i) {
        for (int j = 0; j < GRID_SIZE - 1; ++j) {
            LD gx = (D[i + 1][j] + D[i + 1][j + 1] - D[i][j] - D[i][j + 1]) / (2.0 * C);
            LD gy = (D[i][j + 1] + D[i + 1][j + 1] - D[i][j] - D[i + 1][j]) / (2.0 * C);
            grads[i][j] = {gx, gy};
        }
    }

    std::set<long long> slopes;
    const LD SLOPE_EPS = 1e-7;

    // Find gradient changes between adjacent cells to identify lines
    for (int i = 0; i < GRID_SIZE - 1; ++i) {
        for (int j = 0; j < GRID_SIZE - 1; ++j) {
            // Check horizontally adjacent cell
            if (i + 1 < GRID_SIZE - 1) {
                Vector2D delta_g = {grads[i + 1][j].x - grads[i][j].x, grads[i + 1][j].y - grads[i][j].y};
                if (std::abs(delta_g.x * delta_g.x + delta_g.y * delta_g.y - 4.0) < 0.1) {
                    if (std::abs(delta_g.y) > SLOPE_EPS) {
                        slopes.insert(round(-delta_g.x / delta_g.y));
                    }
                }
            }
            // Check vertically adjacent cell
            if (j + 1 < GRID_SIZE - 1) {
                Vector2D delta_g = {grads[i][j + 1].x - grads[i][j].x, grads[i][j + 1].y - grads[i][j].y};
                if (std::abs(delta_g.x * delta_g.x + delta_g.y * delta_g.y - 4.0) < 0.1) {
                     if (std::abs(delta_g.y) > SLOPE_EPS) {
                        slopes.insert(round(-delta_g.x / delta_g.y));
                    }
                }
            }
        }
    }
    
    std::vector<long long> a(slopes.begin(), slopes.end());
    
    // Phase 2: Find all intercepts b_i
    std::vector<LD> c(N);
    for (int i = 0; i < N; ++i) {
        c[i] = 1.0 / sqrt((LD)a[i] * a[i] + 1.0);
    }

    std::vector<LD> m(N);
    if (N > 0) {
        m[0] = a[0] - 1.0;
        for (int i = 1; i < N; ++i) {
            m[i] = ((LD)a[i] + a[i-1]) / 2.0;
        }
    }

    std::vector<LD> L(N);
    LD X = 1e11;

    // For each m, get a linear equation on b_i
    for (int i = 0; i < N; ++i) {
        LD val1 = query(X, m[i] * X);
        LD val2 = query(X + 1.0, m[i] * (X + 1.0));
        LD slope_term = val2 - val1;
        L[i] = val1 - X * slope_term;
    }
    
    // Build matrix for the linear system Ax=L
    std::vector<std::vector<LD>> A(N, std::vector<LD>(N));
    for (int i = 0; i < N; ++i) { // equation index
        for (int j = 0; j < N; ++j) { // variable index
            A[i][j] = ((LD)a[j] > m[i] ? 1.0 : -1.0) * c[j];
        }
    }
    
    // Solve the system using Gaussian elimination
    for (int i = 0; i < N; ++i) {
        int pivot = i;
        for (int j = i + 1; j < N; ++j) {
            if (std::abs(A[j][i]) > std::abs(A[pivot][i])) {
                pivot = j;
            }
        }
        std::swap(A[i], A[pivot]);
        std::swap(L[i], L[pivot]);

        for (int j = i + 1; j < N; ++j) {
            LD factor = A[j][i] / A[i][i];
            for (int k = i; k < N; ++k) {
                A[j][k] -= factor * A[i][k];
            }
            L[j] -= factor * L[i];
        }
    }
    
    std::vector<LD> b_ld(N);
    for (int i = N - 1; i >= 0; --i) {
        LD sum = 0;
        for (int j = i + 1; j < N; ++j) {
            sum += A[i][j] * b_ld[j];
        }
        b_ld[i] = (L[i] - sum) / A[i][i];
    }
    
    std::vector<long long> b(N);
    for (int i = 0; i < N; ++i) {
        b[i] = round(b_ld[i]);
    }

    // Output the final answer
    std::cout << "! ";
    for (int i = 0; i < N; ++i) std::cout << a[i] << (i == N - 1 ? "" : " ");
    std::cout << " ";
    for (int i = 0; i < N; ++i) std::cout << b[i] << (i == N - 1 ? "" : " ");
    std::cout << std::endl;

    return 0;
}