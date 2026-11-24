frappe.pages['cj-catalogue'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'CJ Product Catalogue',
        single_column: true
    });

    const state = { page: 1, size: 20, keyword: '', products: [], totalPages: 1 };
    const $main = $(page.main);
    $main.html(`
        <div class="prodrop-catalogue">
            <div class="prodrop-toolbar">
                <div>
                    <h3>CJ Product Catalogue</h3>
                    <p>Search CJ Dropshipping products and inspect variants and live stock.</p>
                </div>
                <div class="prodrop-search">
                    <input class="form-control" id="prodrop-keyword"
                        placeholder="Search by product name or SKU">
                    <button class="btn btn-primary" id="prodrop-search">Search</button>
                </div>
            </div>
            <div id="prodrop-status" class="text-muted">Enter a keyword or SKU to begin.</div>
            <div id="prodrop-results" class="prodrop-grid"></div>
            <div id="prodrop-pagination" class="prodrop-pagination"></div>
            <div id="prodrop-detail"></div>
        </div>
    `);

    function esc(value) {
        return String(value ?? '').replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;',
            '"': '&quot;', "'": '&#39;'
        }[c]));
    }

    function imageUrl(value) {
        const url = String(value || '');
        return /^https:\/\/[a-z0-9.-]+\//i.test(url) ? esc(url) : '';
    }

    function getProducts(data) {
        const root = Array.isArray(data?.content) ? data.content[0] : data;
        return root?.productList || data?.productList || [];
    }

    function searchProducts() {
        state.keyword = $('#prodrop-keyword').val().trim();
        state.page = 1;
        loadProducts();
    }

    function loadProducts() {
        $('#prodrop-status').text('Loading products from CJ...');
        $('#prodrop-results').empty();
        $('#prodrop-pagination').empty();
        $('#prodrop-detail').empty();

        frappe.call({
            method: 'prodrop.catalogue.search_products',
            args: {
                keyword: state.keyword || null,
                page: state.page,
                size: state.size
            },
            callback(r) {
                const data = r.message || {};
                state.products = getProducts(data);
                state.totalPages = Number(data.totalPages || 1);

                $('#prodrop-status').text(
                    `${Number(data.totalRecords || state.products.length).toLocaleString()} products found`
                );

                if (!state.products.length) {
                    $('#prodrop-results').html('<p>No products found. Try another search.</p>');
                    return;
                }

                const cards = state.products.map((p, index) => {
                    const img = imageUrl(p.bigImage);
                    return `
                        <div class="prodrop-product-card" data-index="${index}">
                            <div class="prodrop-product-image">
                                ${img ? `<img src="${img}" alt="${esc(p.nameEn)}" loading="lazy">` : '<span>No image</span>'}
                            </div>
                            <div class="prodrop-product-info">
                                <div class="prodrop-product-name">${esc(p.nameEn || p.name || 'Unnamed product')}</div>
                                <div class="text-muted">SKU: ${esc(p.sku || '-')}</div>
                                <div class="prodrop-price">${esc(p.sellPrice || 'Price unavailable')}</div>
                                <button class="btn btn-default btn-sm prodrop-view" data-index="${index}">
                                    View details
                                </button>
                            </div>
                        </div>`;
                }).join('');

                $('#prodrop-results').html(cards);
                renderPagination();
            },
            error() {
                $('#prodrop-status').text('Could not load products. Check the Error Log.');
            }
        });
    }

    function renderPagination() {
        if (state.totalPages <= 1) return;
        $('#prodrop-pagination').html(`
            <button class="btn btn-default" id="prodrop-prev" ${state.page <= 1 ? 'disabled' : ''}>Previous</button>
            <span>Page ${state.page} of ${state.totalPages}</span>
            <button class="btn btn-default" id="prodrop-next" ${state.page >= state.totalPages ? 'disabled' : ''}>Next</button>
        `);
    }

    function showProduct(product) {
        const pid = product.id;
        if (!pid) {
            frappe.msgprint('This CJ product does not have a product ID.');
            return;
        }

        $('#prodrop-detail').html('<div class="prodrop-detail-panel">Loading product details...</div>');
        $('#prodrop-results, #prodrop-pagination').hide();

        frappe.call({
            method: 'prodrop.catalogue.get_product_details',
            args: { pid: String(pid) },
            callback(r) {
                const d = r.message || {};
                const variants = d.variants || [];
                let images = Array.isArray(d.productImageSet) ? d.productImageSet : [];
                images = images.map(x => typeof x === 'string' ? x : (x.imageUrl || x.url || x.bigImage)).filter(Boolean);
                if (d.bigImage && !images.includes(d.bigImage)) images.unshift(d.bigImage);

                const firstImage = images[0] || d.bigImage || '';
                const gallery = images.map((url, i) => `
                    <img class="prodrop-thumb" data-image="${esc(url)}"
                         src="${imageUrl(url)}" alt="Product image ${i + 1}">
                `).join('');

                const variantOptions = variants.map((v, i) => `
                    <option value="${i}">${esc(v.variantKey || v.variantSku || v.vid || `Variant ${i + 1}`)}
                    — ${esc(v.variantSellPrice ?? v.variantSugSellPrice ?? '')}</option>
                `).join('');

                const description = String(d.description || d.descriptionEn || '')
                    .replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

                $('#prodrop-detail').html(`
                    <div class="prodrop-detail-panel">
                        <button class="btn btn-default btn-sm" id="prodrop-back">← Back to products</button>
                        <div class="prodrop-detail-layout">
                            <div>
                                <img id="prodrop-main-image" class="prodrop-main-image"
                                     src="${imageUrl(firstImage)}" alt="${esc(d.productNameEn || '')}">
                                <div class="prodrop-gallery">${gallery}</div>
                            </div>
                            <div>
                                <h3>${esc(d.productNameEn || d.nameEn || 'Product details')}</h3>
                                <p class="text-muted">SKU: ${esc(d.productSku || d.sku || '-')}</p>
                                <h4>${esc(d.sellPrice || product.sellPrice || 'Price unavailable')}</h4>
                                <p>${esc(d.categoryName || '')}</p>
                                <hr>
                                <label>Select variant</label>
                                <select class="form-control" id="prodrop-variant">
                                    ${variantOptions || '<option value="">No variants returned</option>'}
                                </select>
                                <div id="prodrop-variant-info" class="prodrop-stock-box">
                                    ${variants.length ? 'Select a variant to check live stock.' : 'No variants available.'}
                                </div>
                                <p class="text-muted">Stock is checked when you select a variant.</p>
                                <button class="btn btn-primary" disabled>Import workflow coming next</button>
                                <hr>
                                <h5>Product description</h5>
                                <p>${esc(description || 'No description provided.')}</p>
                            </div>
                        </div>
                    </div>
                `);

                $('#prodrop-variant').on('change', function () {
                    const variant = variants[Number(this.value)];
                    if (variant) loadStock(variant);
                });

                $('.prodrop-thumb').on('click', function () {
                    $('#prodrop-main-image').attr('src', $(this).data('image'));
                });

                if (variants.length) {
                    $('#prodrop-variant').trigger('change');
                }
            },
            error() {
                $('#prodrop-detail').html('<p>Could not retrieve product details. Check the Error Log.</p>');
            }
        });
    }

    function loadStock(variant) {
        const $box = $('#prodrop-variant-info');
        $box.text('Checking live CJ stock...');

        frappe.call({
            method: 'prodrop.catalogue.get_variant_stock',
            args: { vid: String(variant.vid) },
            callback(r) {
                const stock = r.message || {};
                const rows = Array.isArray(stock) ? stock : [stock];
                const html = rows.map(s => `
                    <div><strong>Warehouse:</strong> ${esc(s.areaEn || s.countryCode || 'CJ')}</div>
                    <div><strong>CJ inventory:</strong> ${esc(s.cjInventoryNum ?? 'Unavailable')}</div>
                    <div><strong>Factory inventory:</strong> ${esc(s.factoryInventoryNum ?? 'Unavailable')}</div>
                    <div><strong>Total inventory:</strong> ${esc(s.totalInventoryNum ?? s.storageNum ?? 'Unavailable')}</div>
                `).join('');
                $box.html(html || 'CJ returned no stock details.');
            },
            error() {
                $box.text('Stock lookup failed. Check the Error Log.');
            }
        });
    }

    $main.on('click', '#prodrop-search', searchProducts);
    $main.on('keydown', '#prodrop-keyword', e => {
        if (e.key === 'Enter') searchProducts();
    });
    $main.on('click', '.prodrop-view', function () {
        showProduct(state.products[Number($(this).data('index'))]);
    });
    $main.on('click', '#prodrop-back', function () {
        $('#prodrop-detail').empty();
        $('#prodrop-results, #prodrop-pagination').show();
    });
    $main.on('click', '#prodrop-prev', function () {
        if (state.page > 1) { state.page--; loadProducts(); }
    });
    $main.on('click', '#prodrop-next', function () {
        if (state.page < state.totalPages) { state.page++; loadProducts(); }
    });

    page.set_primary_action('Search products', searchProducts, 'search');
};

frappe.pages['cj-catalogue'].on_page_show = function () {
    // Page is ready; the user can start a search.
};
