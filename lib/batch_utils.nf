def toJson(article_list) {
    def json = groovy.json.JsonOutput.toJson(article_list)
    json = groovy.json.JsonOutput.prettyPrint(json)
    def tempFile = File.createTempFile("articles_", ".json")
    tempFile.write(json)
    return file(tempFile)
}

def batchFlattened(channel, batch_size) {
    def result = channel
        .buffer(size: batch_size, remainder: true)
        .map { batch -> toJson(batch) }

    return params.debug ? result.take(2) : result
}

def batchArticles(channel, batch_size) {
    def result = channel
        .splitJson()
        .flatten()
        .buffer(size: batch_size, remainder: true)
        .map { batch -> toJson(batch) }

    return params.debug ? result.take(2) : result
}

def filterAndBatch(channel, batch_size, key, value) {

    if (!key || !value) {
        error "Both key and value must be provided for filtering."
    }

    def branches = channel
        .splitJson()
        .flatten()
        .branch {
            match: it[key] == value
            no_match: it[key] != value
        }

    return [
        match: batchFlattened(branches.match, batch_size),
        no_match: batchFlattened(branches.no_match, batch_size)
    ]
}
